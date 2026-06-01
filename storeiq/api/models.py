"""Pydantic request and response models."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class EventIngest(BaseModel):
    """Request body for event ingestion — matches problem statement schema."""

    event_id: UUID
    store_id: str = "STORE_BLR_002"
    event_type: str
    visitor_id: str
    camera_id: Optional[str] = None
    zone_id: Optional[str] = None
    timestamp: datetime
    is_staff: bool = False
    confidence: float = 0.0
    dwell_ms: int = 0
    metadata: Dict[str, object] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "event_id": "7b0a8a4c-0c1f-4d20-9bdb-8c3bb5a4c8b8",
                "store_id": "STORE_BLR_002",
                "event_type": "ENTRY",
                "visitor_id": "VIS_c8a2f1",
                "camera_id": "CAM_ENTRY_01",
                "zone_id": "ENTRANCE",
                "timestamp": "2026-04-10T14:22:10Z",
                "is_staff": False,
                "confidence": 0.91,
                "dwell_ms": 0,
                "metadata": {"queue_depth": None, "sku_zone": None, "session_seq": 1},
            }
        }
    }


class EventAccepted(BaseModel):
    """Response for accepted event ingestion."""

    status: str
    event_id: str


class BatchIngestRequest(BaseModel):
    """Request body for batch event ingestion (up to 500 events)."""

    events: List[EventIngest] = Field(..., max_length=500)


class BatchIngestResult(BaseModel):
    """Result for a single event in batch processing."""

    event_id: str
    status: str
    error: Optional[str] = None


class BatchIngestResponse(BaseModel):
    """Response for batch event ingestion with partial success."""

    accepted: int
    rejected: int
    results: List[BatchIngestResult]


class MetricsResponse(BaseModel):
    """Aggregated metrics response — matches problem statement spec."""

    unique_visitors: int
    current_in_store: int
    avg_dwell_minutes: float
    conversion_rate: float
    queue_depth: int
    abandonment_rate: float = 0.0
    peak_hour: str
    zone_scores: Dict[str, int]
    avg_dwell_per_zone: Dict[str, float] = Field(default_factory=dict)

    model_config = {
        "json_schema_extra": {
            "example": {
                "unique_visitors": 245,
                "current_in_store": 18,
                "avg_dwell_minutes": 7.4,
                "conversion_rate": 12.8,
                "queue_depth": 3,
                "abandonment_rate": 8.5,
                "peak_hour": "18:00",
                "zone_scores": {"SKINCARE": 82, "MAKEUP": 65, "HAIRCARE": 41, "BILLING": 55},
                "avg_dwell_per_zone": {"SKINCARE": 5.2, "MAKEUP": 3.1, "HAIRCARE": 2.8, "BILLING": 1.5},
            }
        }
    }


class FunnelStage(BaseModel):
    """Funnel stage response item."""

    stage: str
    count: int
    pct: float


class FunnelResponse(BaseModel):
    """Funnel response payload."""

    stages: List[FunnelStage]
    drop_off_alert: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "stages": [
                    {"stage": "ENTRY", "count": 245, "pct": 100.0},
                    {"stage": "ZONE_VISIT", "count": 198, "pct": 80.8},
                    {"stage": "BILLING", "count": 72, "pct": 29.4},
                    {"stage": "PURCHASE", "count": 31, "pct": 12.7},
                ],
                "drop_off_alert": "BILLING→PURCHASE drop-off is 56.9% — above 50% threshold",
            }
        }
    }


class HeatmapZone(BaseModel):
    """Heatmap zone data with visit count and avg dwell."""

    visit_count: int
    avg_dwell_minutes: float
    score: int


class HeatmapResponse(BaseModel):
    """Heatmap response payload — enhanced with dwell and confidence."""

    zones: Dict[str, int]
    zone_details: Dict[str, HeatmapZone] = Field(default_factory=dict)
    data_confidence: str = "HIGH"

    model_config = {
        "json_schema_extra": {
            "example": {
                "zones": {"SKINCARE": 82, "MAKEUP": 65, "HAIRCARE": 41, "BILLING": 55},
                "zone_details": {
                    "SKINCARE": {"visit_count": 82, "avg_dwell_minutes": 5.2, "score": 82},
                },
                "data_confidence": "HIGH",
            }
        }
    }


class AnomalyItem(BaseModel):
    """Anomaly response item — includes suggested_action."""

    anomaly_id: str
    type: str
    severity: str
    confidence: float
    reason: str
    suggested_action: Optional[str] = None
    zone_id: Optional[str] = None
    created_at: datetime


class AnomaliesResponse(BaseModel):
    """Anomalies response payload."""

    anomalies: List[AnomalyItem]

    model_config = {
        "json_schema_extra": {
            "example": {
                "anomalies": [
                    {
                        "anomaly_id": "0b6ddaf7-3a89-45c0-9a7a-8ebcfb8c0f83",
                        "type": "QUEUE_SPIKE",
                        "severity": "CRITICAL",
                        "confidence": 0.94,
                        "reason": "Queue depth 3.2σ above 7-day rolling baseline",
                        "suggested_action": "Open additional billing counter immediately",
                        "zone_id": "BILLING",
                        "created_at": "2026-04-10T14:23:11Z",
                    }
                ]
            }
        }
    }


class QueuePredictionResponse(BaseModel):
    """Queue prediction response payload."""

    current_queue: int
    forecast_10min: int
    forecast_30min: int
    confidence: float
    recommendation: str

    model_config = {
        "json_schema_extra": {
            "example": {
                "current_queue": 8,
                "forecast_10min": 14,
                "forecast_30min": 11,
                "confidence": 0.81,
                "recommendation": "Open additional billing counter in next 5 minutes",
            }
        }
    }


class StoreHealthDetail(BaseModel):
    """Per-store health detail."""

    store_id: str
    last_event: Optional[datetime] = None
    status: str = "healthy"
    warning: Optional[str] = None


class HealthResponse(BaseModel):
    """Health status response payload."""

    status: str
    last_event: Optional[datetime] = None
    uptime_sec: int
    warning: Optional[str] = None
    stores: List[StoreHealthDetail] = Field(default_factory=list)

    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "healthy",
                "last_event": "2026-04-10T14:23:11Z",
                "uptime_sec": 3820,
                "stores": [
                    {
                        "store_id": "STORE_BLR_002",
                        "last_event": "2026-04-10T14:23:11Z",
                        "status": "healthy",
                    }
                ],
            }
        }
    }
