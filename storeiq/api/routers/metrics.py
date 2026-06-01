"""Metrics API router — store-scoped."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from api.rate_limit import limiter
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
import orjson

from api.models import MetricsResponse
from api.config import get_settings
from api.db import SessionLocal, get_db
from api.live_data import build_live_payload, compute_store_metrics


router = APIRouter()
settings = get_settings()


def get_live_payload(_state) -> Dict[str, object]:
    """Build the payload pushed over WebSockets from live DB queries."""
    db = SessionLocal()
    try:
        return build_live_payload(db, "STORE_BLR_002")
    finally:
        db.close()


@router.get("/stores/{store_id}/metrics", response_model=MetricsResponse)
@limiter.limit("60/minute")
async def get_store_metrics(
    store_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> MetricsResponse:
    """Return live metrics for a specific store, excluding staff events."""
    payload = compute_store_metrics(db, store_id)
    request.app.state.redis.set("live:metrics", orjson.dumps(payload.model_dump()))
    return payload


# Keep the legacy endpoint for backward compatibility
@router.get("/metrics", response_model=MetricsResponse)
@limiter.limit("60/minute")
async def get_metrics(request: Request, db: Session = Depends(get_db)) -> MetricsResponse:
    """Return metrics — legacy endpoint, defaults to STORE_BLR_002."""
    return await get_store_metrics("STORE_BLR_002", request, db)
