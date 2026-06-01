"""Funnel API router — store-scoped."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.models import FunnelResponse, FunnelStage
from api.db import get_db
from analytics.funnel_engine import FunnelEngine


router = APIRouter()


@router.get("/stores/{store_id}/funnel", response_model=FunnelResponse)
async def get_store_funnel(store_id: str, db: Session = Depends(get_db)) -> FunnelResponse:
    """Return funnel metrics for a specific store.

    Sessions are the unit. Re-entries do not double-count a visitor.
    Purchase stage uses POS transaction correlation.
    """
    engine = FunnelEngine()
    stages = engine.compute(db, store_id=store_id)
    return FunnelResponse(
        stages=[FunnelStage(**stage) for stage in stages],
        drop_off_alert=engine.drop_off_alert(stages),
    )


# Legacy endpoint
@router.get("/funnel", response_model=FunnelResponse)
async def get_funnel(db: Session = Depends(get_db)) -> FunnelResponse:
    """Return funnel metrics — legacy endpoint, defaults to STORE_BLR_002."""
    return await get_store_funnel("STORE_BLR_002", db)
