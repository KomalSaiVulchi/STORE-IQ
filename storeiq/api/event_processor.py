"""Persist pipeline/Kafka events and update sessions + live anomalies."""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from anomaly.anomaly_engine import AnomalyEngine
from database.models import AnomalyRecord, Event, MetricsHourly, PosTransaction, SessionRecord

logger = logging.getLogger("storeiq-api")

SUGGESTED_ACTIONS = {
    "QUEUE_SPIKE": "Open additional billing counter immediately to reduce wait time",
    "CONVERSION_DROP": "Review product placement and promotions in high-traffic zones",
    "DEAD_ZONE": "Investigate zone layout — consider staff redirection or promotional signage",
    "CAMERA_OFFLINE": "Check camera hardware and network connectivity; dispatch maintenance",
    "CROWD_ALERT": "Consider crowd management measures; limit new entries if near capacity",
}


def _parse_timestamp(value: Any) -> datetime:
    """Parse epoch float or ISO string into UTC datetime."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc)
    if isinstance(value, str):
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc)


def persist_event(db: Session, payload: Dict[str, Any]) -> Optional[Event]:
    """Insert an event idempotently and update session state."""
    event_id = str(payload.get("event_id", ""))
    if not event_id:
        return None

    existing = db.query(Event).filter(Event.event_id == event_id).one_or_none()
    if existing:
        return existing

    store_id = payload.get("store_id", "STORE_BLR_002")
    event_type = payload.get("event_type", "")
    visitor_id = payload.get("visitor_id", "")
    timestamp = _parse_timestamp(payload.get("timestamp"))
    metadata = payload.get("metadata") or {}

    record = Event(
        event_id=event_id,
        store_id=store_id,
        event_type=event_type,
        visitor_id=visitor_id,
        track_id=payload.get("track_id"),
        camera_id=payload.get("camera_id"),
        zone_id=payload.get("zone_id"),
        timestamp=timestamp,
        is_staff=bool(payload.get("is_staff", False)),
        confidence=float(payload.get("confidence", 0.0) or 0.0),
        dwell_ms=int(payload.get("dwell_ms", 0) or 0),
        metadata_json=metadata if isinstance(metadata, dict) else {},
    )

    if event_type == "BILLING_QUEUE_ABANDON" and _has_pos_after(db, record):
        return None

    db.add(record)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        duplicate = db.query(Event).filter(Event.event_id == event_id).one_or_none()
        if duplicate:
            return duplicate
        raise

    _update_session(db, record)
    return record


def _update_session(db: Session, event: Event) -> None:
    """Update session records based on event type."""
    if event.is_staff:
        return

    if event.event_type == "ENTRY":
        _open_session(db, event, reentry=False)
    elif event.event_type == "REENTRY":
        _open_session(db, event, reentry=True)
    elif event.event_type == "ZONE_ENTER" and event.zone_id:
        session = (
            db.query(SessionRecord)
            .filter(SessionRecord.visitor_id == event.visitor_id, SessionRecord.exit_time.is_(None))
            .order_by(SessionRecord.entry_time.desc())
            .first()
        )
        if session:
            zones = list(session.zones_visited or [])
            if event.zone_id not in zones:
                zones.append(event.zone_id)
            session.zones_visited = zones
            if event.zone_id == "BILLING":
                session.billing_visited = True
            db.commit()
    elif event.event_type == "BILLING_QUEUE_ABANDON":
        pass  # invalid abandons are not persisted
    elif event.event_type == "EXIT":
        session = (
            db.query(SessionRecord)
            .filter(SessionRecord.visitor_id == event.visitor_id, SessionRecord.exit_time.is_(None))
            .order_by(SessionRecord.entry_time.desc())
            .first()
        )
        if session:
            session.exit_time = event.timestamp
            session.dwell_seconds = int((event.timestamp - session.entry_time).total_seconds())
            db.commit()
            mark_pos_purchases(db, event.store_id)


def _has_pos_after(db: Session, event: Event) -> bool:
    """Return True if a POS transaction occurs within 5 minutes after the event."""
    window_end = event.timestamp + timedelta(minutes=5)
    txn = (
        db.query(PosTransaction)
        .filter(
            PosTransaction.store_id == event.store_id,
            PosTransaction.timestamp >= event.timestamp,
            PosTransaction.timestamp <= window_end,
        )
        .first()
    )
    return txn is not None


def mark_pos_purchases(db: Session, store_id: Optional[str] = None) -> int:
    """Mark sessions as purchased when billing overlaps POS transaction window."""
    pos_query = db.query(PosTransaction)
    if store_id:
        pos_query = pos_query.filter(PosTransaction.store_id == store_id)
    transactions = pos_query.all()
    if not transactions:
        return 0

    marked = 0
    for txn in transactions:
        window_start = txn.timestamp - timedelta(minutes=5)
        window_end = txn.timestamp
        sessions = db.query(SessionRecord).filter(
            SessionRecord.billing_visited.is_(True),
            SessionRecord.entry_time <= window_end,
        )
        if store_id:
            sessions = sessions.filter(SessionRecord.store_id == store_id)

        for session in sessions.all():
            end_time = session.exit_time or window_end
            if session.entry_time <= window_end and end_time >= window_start:
                if not session.purchase:
                    session.purchase = True
                    marked += 1
    if marked:
        db.commit()
    return marked


def _open_session(db: Session, event: Event, reentry: bool) -> None:
    """Open a new visitor session."""
    open_session = (
        db.query(SessionRecord)
        .filter(SessionRecord.visitor_id == event.visitor_id, SessionRecord.exit_time.is_(None))
        .one_or_none()
    )
    if open_session:
        return

    session_id = str(uuid.uuid4())
    zones = [event.zone_id] if event.zone_id else []
    record = SessionRecord(
        session_id=session_id,
        store_id=event.store_id,
        visitor_id=event.visitor_id,
        entry_time=event.timestamp,
        zones_visited=zones,
        billing_visited=event.zone_id == "BILLING",
        purchase=False,
        dwell_seconds=0,
        reentry=reentry,
        camera_path=[event.camera_id] if event.camera_id else [],
    )
    db.add(record)
    db.commit()


def evaluate_live_anomalies(db: Session, store_id: str = "STORE_BLR_002") -> None:
    """Evaluate and persist live anomalies from current metrics."""
    engine = AnomalyEngine()
    hourly = (
        db.query(MetricsHourly)
        .filter(MetricsHourly.hour_bucket.isnot(None))
        .order_by(MetricsHourly.hour_bucket.desc())
        .limit(24)
        .all()
    )
    queue_baseline = [float(h.queue_depth_avg or 0) for h in hourly]
    conversion_baseline = [float(h.conversion_rate or 0) for h in hourly if h.conversion_rate]

    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    from sqlalchemy import func

    current_queue = (
        db.query(func.count(Event.id))
        .filter(
            Event.store_id == store_id,
            Event.event_type == "BILLING_QUEUE_JOIN",
            Event.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=10),
        )
        .scalar()
        or 0
    )
    total_sessions = (
        db.query(SessionRecord)
        .filter(SessionRecord.store_id == store_id, SessionRecord.entry_time >= today_start)
        .count()
    )
    purchase_sessions = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.entry_time >= today_start,
            SessionRecord.purchase.is_(True),
        )
        .count()
    )
    current_conversion = (purchase_sessions / total_sessions * 100) if total_sessions else 0.0
    weekly_avg = sum(conversion_baseline) / len(conversion_baseline) if conversion_baseline else current_conversion

    in_store = (
        db.query(SessionRecord)
        .filter(SessionRecord.store_id == store_id, SessionRecord.exit_time.is_(None))
        .count()
    )

    candidates = []
    if result := engine.queue_spike(float(current_queue), queue_baseline):
        candidates.append(result)
    if result := engine.conversion_drop(current_conversion, weekly_avg):
        candidates.append(result)
    if result := engine.crowd_alert(in_store, 120):
        candidates.append(result)

    for zone in ["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING"]:
        visits = (
            db.query(func.count(Event.id))
            .filter(
                Event.store_id == store_id,
                Event.zone_id == zone,
                Event.event_type == "ZONE_ENTER",
                Event.timestamp >= datetime.now(timezone.utc) - timedelta(minutes=30),
                Event.is_staff.is_(False),
            )
            .scalar()
            or 0
        )
        if result := engine.dead_zone(visits, 30, zone):
            candidates.append(result)

    for result in candidates:
        _upsert_anomaly(db, store_id, result)


def _upsert_anomaly(db: Session, store_id: str, result) -> None:
    """Insert anomaly if no active duplicate of same type+zone exists."""
    existing = (
        db.query(AnomalyRecord)
        .filter(
            AnomalyRecord.store_id == store_id,
            AnomalyRecord.type == result.type,
            AnomalyRecord.zone_id == result.zone_id,
            AnomalyRecord.resolved.is_(False),
        )
        .one_or_none()
    )
    if existing:
        existing.confidence = result.confidence
        existing.reason = result.reason
        db.commit()
        return

    db.add(
        AnomalyRecord(
            anomaly_id=str(uuid.uuid4()),
            store_id=store_id,
            type=result.type,
            severity=result.severity,
            confidence=result.confidence,
            reason=result.reason,
            suggested_action=SUGGESTED_ACTIONS.get(result.type, "Monitor and investigate"),
            zone_id=result.zone_id,
            resolved=False,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.commit()
