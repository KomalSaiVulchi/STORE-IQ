"""Anomalies API router — store-scoped with suggested_action."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from api.models import AnomaliesResponse, AnomalyItem
from api.db import get_db
from database.models import AnomalyRecord


router = APIRouter()

# Default suggested actions by anomaly type
SUGGESTED_ACTIONS = {
    "QUEUE_SPIKE": "Open additional billing counter immediately to reduce wait time",
    "CONVERSION_DROP": "Review product placement and promotions in high-traffic zones",
    "DEAD_ZONE": "Investigate zone layout — consider staff redirection or promotional signage",
    "CAMERA_OFFLINE": "Check camera hardware and network connectivity; dispatch maintenance",
    "CROWD_ALERT": "Consider crowd management measures; limit new entries if near capacity",
    "STALE_FEED": "Check pipeline health and camera feed connectivity",
    "BILLING_QUEUE_SPIKE": "Deploy additional billing staff to reduce queue abandonment",
}


@router.get("/stores/{store_id}/anomalies", response_model=AnomaliesResponse)
async def get_store_anomalies(
    store_id: str,
    active_only: bool = Query(default=True),
    severity: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> AnomaliesResponse:
    """Return anomaly list for a specific store with optional filtering.

    Severity levels: INFO, WARN, CRITICAL.
    Each anomaly includes a suggested_action string.
    """
    query = db.query(AnomalyRecord).filter(AnomalyRecord.store_id == store_id)
    if active_only:
        query = query.filter(AnomalyRecord.resolved.is_(False))
    if severity:
        query = query.filter(AnomalyRecord.severity == severity)
    records = query.order_by(AnomalyRecord.created_at.desc()).all()

    return AnomaliesResponse(
        anomalies=[
            AnomalyItem(
                anomaly_id=record.anomaly_id,
                type=record.type,
                severity=record.severity,
                confidence=float(record.confidence or 0),
                reason=record.reason or "",
                suggested_action=record.suggested_action or SUGGESTED_ACTIONS.get(record.type, "Monitor and investigate"),
                zone_id=record.zone_id,
                created_at=record.created_at,
            )
            for record in records
        ]
    )


# Legacy endpoint
@router.get("/anomalies", response_model=AnomaliesResponse)
async def get_anomalies(
    active_only: bool = Query(default=True),
    severity: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
) -> AnomaliesResponse:
    """Return anomalies — legacy endpoint, defaults to STORE_BLR_002."""
    return await get_store_anomalies("STORE_BLR_002", active_only, severity, db)
