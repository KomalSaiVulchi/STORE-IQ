"""Heatmap API router — store-scoped with data confidence."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models import HeatmapResponse, HeatmapZone
from api.db import get_db
from database.models import Event, MetricsHourly, SessionRecord


router = APIRouter()


@router.get("/stores/{store_id}/heatmap", response_model=HeatmapResponse)
async def get_store_heatmap(store_id: str, db: Session = Depends(get_db)) -> HeatmapResponse:
    """Return zone heatmap scores for a specific store.

    Includes visit frequency, avg dwell, and data_confidence flag
    (LOW if fewer than 20 sessions in the window).
    """
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Zone visit counts from events
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

    # Zone avg dwell
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
    dwell_map = {zone: (dwell or 0) / 60000 for zone, dwell in zone_dwell}

    # Normalize to 0-100
    max_count = max((c for _, c in zone_counts), default=1) or 1
    scores = {}
    zone_details = {}
    for zone, count in zone_counts:
        score = int(round(count / max_count * 100))
        scores[zone] = score
        zone_details[zone] = HeatmapZone(
            visit_count=count,
            avg_dwell_minutes=round(dwell_map.get(zone, 0), 1),
            score=score,
        )

    # Ensure all standard zones present
    for zone in ["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING", "ENTRANCE"]:
        scores.setdefault(zone, 0)

    # Fallback to seed data if no events
    if not zone_counts:
        latest = db.query(MetricsHourly).order_by(MetricsHourly.hour_bucket.desc()).first()
        if latest and latest.zone_scores:
            scores = {k: int(round(v)) for k, v in latest.zone_scores.items()}
        for zone in ["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING", "ENTRANCE"]:
            scores.setdefault(zone, 0)

    # Data confidence check
    session_count = (
        db.query(SessionRecord)
        .filter(
            SessionRecord.store_id == store_id,
            SessionRecord.entry_time >= today_start,
        )
        .count()
    )
    data_confidence = "HIGH" if session_count >= 20 else "LOW"

    return HeatmapResponse(
        zones=scores,
        zone_details=zone_details,
        data_confidence=data_confidence,
    )


# Legacy endpoint
@router.get("/heatmap", response_model=HeatmapResponse)
async def get_heatmap(db: Session = Depends(get_db)) -> HeatmapResponse:
    """Return heatmap — legacy endpoint, defaults to STORE_BLR_002."""
    return await get_store_heatmap("STORE_BLR_002", db)
