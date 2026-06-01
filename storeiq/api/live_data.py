"""Build live dashboard payloads from database queries."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Dict, List

from sqlalchemy import func
from sqlalchemy.orm import Session

from analytics.funnel_engine import FunnelEngine
from analytics.prediction_engine import PredictionEngine
from api.models import MetricsResponse
from api.event_processor import mark_pos_purchases
from database.models import AnomalyRecord, Event, MetricsHourly, SessionRecord


def _metrics_window_start(db: Session, store_id: str, now: datetime) -> datetime:
    """Metrics window: calendar today if busy, else the day with the most visitor events."""
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_count = (
        db.query(func.count(Event.id))
        .filter(
            Event.store_id == store_id,
            Event.timestamp >= today_start,
            Event.is_staff.is_(False),
        )
        .scalar()
        or 0
    )
    if today_count >= 10:
        return today_start

    busiest = (
        db.query(
            func.date_trunc("day", Event.timestamp).label("day"),
            func.count(Event.id).label("cnt"),
        )
        .filter(Event.store_id == store_id, Event.is_staff.is_(False))
        .group_by("day")
        .order_by(func.count(Event.id).desc())
        .first()
    )
    if busiest and busiest[0]:
        day = busiest[0]
        return day.replace(hour=0, minute=0, second=0, microsecond=0)
    return today_start


def compute_store_metrics(db: Session, store_id: str) -> MetricsResponse:
    """Compute store metrics from events and sessions."""
    now = datetime.now(timezone.utc)
    today_start = _metrics_window_start(db, store_id, now)

    unique_visitors = (
        db.query(func.count(func.distinct(Event.visitor_id)))
        .filter(
            Event.store_id == store_id,
            Event.timestamp >= today_start,
            Event.is_staff.is_(False),
            Event.event_type == "ENTRY",
        )
        .scalar()
        or 0
    )

    current_in_store = (
        db.query(SessionRecord)
        .filter(SessionRecord.store_id == store_id, SessionRecord.exit_time.is_(None))
        .count()
    )

    avg_dwell_result = (
        db.query(func.avg(SessionRecord.dwell_seconds))
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.entry_time >= today_start,
            SessionRecord.exit_time.isnot(None),
        )
        .scalar()
    )
    avg_dwell_minutes = round((avg_dwell_result or 0) / 60, 1)

    total_sessions = (
        db.query(SessionRecord)
        .filter(SessionRecord.store_id == store_id, SessionRecord.entry_time >= today_start)
        .count()
    )

    billing_in_zone = (
        db.query(Event)
        .filter(
            Event.store_id == store_id,
            Event.event_type == "BILLING_QUEUE_JOIN",
            Event.timestamp >= now - timedelta(minutes=10),
        )
        .count()
    )

    billing_joins = (
        db.query(Event)
        .filter(
            Event.store_id == store_id,
            Event.event_type == "BILLING_QUEUE_JOIN",
            Event.timestamp >= today_start,
        )
        .count()
    )
    billing_abandons = (
        db.query(Event)
        .filter(
            Event.store_id == store_id,
            Event.event_type == "BILLING_QUEUE_ABANDON",
            Event.timestamp >= today_start,
        )
        .count()
    )
    abandonment_rate = round((billing_abandons / billing_joins * 100), 1) if billing_joins else 0.0

    zone_counts = (
        db.query(Event.zone_id, func.count(Event.id))
        .filter(
            Event.store_id == store_id,
            Event.timestamp >= today_start,
            Event.zone_id.isnot(None),
            Event.is_staff.is_(False),
            Event.event_type == "ZONE_ENTER",
        )
        .group_by(Event.zone_id)
        .all()
    )
    max_count = max((c for _, c in zone_counts), default=1) or 1
    zone_scores = {zone: int(round(count / max_count * 100)) for zone, count in zone_counts}
    for zone in ["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING", "ENTRANCE"]:
        zone_scores.setdefault(zone, 0)

    zone_dwell = (
        db.query(Event.zone_id, func.avg(Event.dwell_ms))
        .filter(
            Event.store_id == store_id,
            Event.timestamp >= today_start,
            Event.zone_id.isnot(None),
            Event.event_type == "ZONE_DWELL",
            Event.is_staff.is_(False),
        )
        .group_by(Event.zone_id)
        .all()
    )
    avg_dwell_per_zone = {zone: round((dwell or 0) / 60000, 1) for zone, dwell in zone_dwell}

    peak_hour_result = (
        db.query(
            func.date_trunc("hour", Event.timestamp).label("hour"),
            func.count(func.distinct(Event.visitor_id)),
        )
        .filter(
            Event.store_id == store_id,
            Event.timestamp >= today_start,
            Event.event_type == "ENTRY",
            Event.is_staff.is_(False),
        )
        .group_by("hour")
        .order_by(func.count(func.distinct(Event.visitor_id)).desc())
        .first()
    )
    peak_hour = peak_hour_result[0].strftime("%H:00") if peak_hour_result else "--:--"

    mark_pos_purchases(db, store_id)

    purchase_sessions = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.entry_time >= today_start,
            SessionRecord.purchase.is_(True),
        )
        .count()
    )
    conversion_rate = round((purchase_sessions / total_sessions * 100), 1) if total_sessions else 0.0

    return MetricsResponse(
        unique_visitors=unique_visitors,
        current_in_store=current_in_store,
        avg_dwell_minutes=avg_dwell_minutes,
        conversion_rate=conversion_rate,
        queue_depth=billing_in_zone,
        abandonment_rate=abandonment_rate,
        peak_hour=peak_hour,
        zone_scores=zone_scores,
        avg_dwell_per_zone=avg_dwell_per_zone,
    )


def _peak_hours(db: Session) -> List[Dict[str, object]]:
    """Return hourly visitor counts for the peak hours chart."""
    records = (
        db.query(MetricsHourly)
        .order_by(MetricsHourly.hour_bucket.asc())
        .limit(24)
        .all()
    )
    if records:
        return [
            {
                "hour": record.hour_bucket.strftime("%H:00"),
                "visitors": int(record.unique_visitors or 0),
            }
            for record in records
        ]

    # Build from today's entry events when seed/metrics tables are empty
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hourly = (
        db.query(
            func.date_trunc("hour", Event.timestamp).label("hour"),
            func.count(func.distinct(Event.visitor_id)),
        )
        .filter(
            Event.timestamp >= today_start,
            Event.event_type == "ENTRY",
            Event.is_staff.is_(False),
        )
        .group_by("hour")
        .order_by("hour")
        .all()
    )
    return [{"hour": hour.strftime("%H:00"), "visitors": count} for hour, count in hourly]


def _anomalies(db: Session, store_id: str) -> List[Dict[str, object]]:
    """Return active anomalies for the dashboard feed."""
    records = (
        db.query(AnomalyRecord)
        .filter(AnomalyRecord.store_id == store_id, AnomalyRecord.resolved.is_(False))
        .order_by(AnomalyRecord.created_at.desc())
        .limit(10)
        .all()
    )
    now = datetime.now(timezone.utc)
    items = []
    for record in records:
        delta = now - record.created_at
        minutes = max(1, int(delta.total_seconds() // 60))
        items.append(
            {
                "anomaly_id": record.anomaly_id,
                "type": record.type,
                "severity": record.severity,
                "confidence": float(record.confidence or 0),
                "reason": record.reason or "",
                "suggested_action": record.suggested_action,
                "zone_id": record.zone_id,
                "created_at": record.created_at.isoformat(),
                "timestamp": f"{minutes}m ago",
            }
        )
    return items


def build_live_payload(db: Session, store_id: str = "STORE_BLR_002") -> Dict[str, object]:
    """Build the full live payload for WebSocket broadcasts."""
    metrics = compute_store_metrics(db, store_id)
    funnel_engine = FunnelEngine()
    funnel_stages = funnel_engine.compute(db, store_id=store_id)

    hourly_records = (
        db.query(MetricsHourly)
        .order_by(MetricsHourly.hour_bucket.desc())
        .limit(24)
        .all()
    )
    prediction_engine = PredictionEngine()
    queue_forecast = prediction_engine.forecast(hourly_records)

    return {
        "metrics": metrics.model_dump(),
        "funnel": funnel_stages,
        "funnel_alert": funnel_engine.drop_off_alert(funnel_stages),
        "peak_hours": _peak_hours(db),
        "queue_forecast": queue_forecast,
        "anomalies": _anomalies(db, store_id),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
