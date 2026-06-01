"""Health API router — with per-store health breakdown."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request
from sqlalchemy import func, distinct
from sqlalchemy.orm import Session

from api.models import HealthResponse, StoreHealthDetail
from api.config import get_settings
from api.db import get_db
from database.models import Event


router = APIRouter()
settings = get_settings()


@router.get("/health", response_model=HealthResponse)
async def health(request: Request, db: Session = Depends(get_db)) -> HealthResponse:
    """Return health status with per-store last event timestamps and stale feed alerts.

    STALE_FEED warning if any store has >10 min lag since last event.
    """
    now = datetime.now(timezone.utc)
    uptime = int(now.timestamp() - request.app.state.started_at)

    # Global last event
    latest = db.query(Event).order_by(Event.timestamp.desc()).first()
    last_event = latest.timestamp if latest else None

    # Per-store health
    store_ids = db.query(distinct(Event.store_id)).all()
    stores = []
    overall_status = "healthy"
    overall_warning = None

    if not store_ids:
        overall_status = "degraded"
        overall_warning = "STALE_FEED"

    for (store_id,) in store_ids:
        store_latest = (
            db.query(Event)
            .filter(Event.store_id == store_id)
            .order_by(Event.timestamp.desc())
            .first()
        )
        store_last_event = store_latest.timestamp if store_latest else None
        store_status = "healthy"
        store_warning = None

        if store_last_event:
            delta = now - store_last_event
            if delta.total_seconds() > settings.stale_feed_minutes * 60:
                store_status = "degraded"
                store_warning = "STALE_FEED"
                overall_status = "degraded"
                overall_warning = "STALE_FEED"
        else:
            store_status = "degraded"
            store_warning = "STALE_FEED"
            overall_status = "degraded"
            overall_warning = "STALE_FEED"

        stores.append(
            StoreHealthDetail(
                store_id=store_id,
                last_event=store_last_event,
                status=store_status,
                warning=store_warning,
            )
        )

    # Check global last event
    if last_event:
        delta = now - last_event
        if delta.total_seconds() > settings.stale_feed_minutes * 60:
            overall_status = "degraded"
            overall_warning = "STALE_FEED"
    else:
        overall_status = "degraded"
        overall_warning = "STALE_FEED"

    return HealthResponse(
        status=overall_status,
        last_event=last_event,
        uptime_sec=uptime,
        warning=overall_warning,
        stores=stores,
    )
