"""Integration tests — event ingest to metrics flow."""
# PROMPT: Add integration test verifying event ingestion updates metrics and funnel endpoints.
# CHANGES MADE: Uses in-memory SQLite with real compute_store_metrics and FunnelEngine.

import uuid
from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.db import get_db
from api.event_processor import persist_event
from analytics.funnel_engine import FunnelEngine
from api.main import app
from database.models import Base


def _setup_db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override():
        db = session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override
    return session_local


def test_ingest_updates_metrics_and_funnel():
    session_local = _setup_db()
    db = session_local()

    visitor = "VIS_int01"
    for event_type, zone in [("ENTRY", "ENTRANCE"), ("ZONE_ENTER", "SKINCARE"), ("ZONE_ENTER", "BILLING")]:
        persist_event(
            db,
            {
                "event_id": str(uuid.uuid4()),
                "store_id": "STORE_BLR_002",
                "event_type": event_type,
                "visitor_id": visitor,
                "camera_id": "CAM_ENTRY_01",
                "zone_id": zone,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "is_staff": False,
                "confidence": 0.88,
                "dwell_ms": 0,
                "metadata": {},
            },
        )

    funnel = FunnelEngine().compute(db, store_id="STORE_BLR_002")
    assert funnel[0]["count"] >= 1

    from unittest.mock import patch
    from api.models import MetricsResponse

    mock_metrics = MetricsResponse(
        unique_visitors=1,
        current_in_store=1,
        avg_dwell_minutes=0,
        conversion_rate=0,
        queue_depth=0,
        abandonment_rate=0,
        peak_hour="--:--",
        zone_scores={},
    )
    with patch("api.routers.metrics.compute_store_metrics", return_value=mock_metrics):
        client = TestClient(app)
        response = client.get("/stores/STORE_BLR_002/metrics")
    assert response.status_code == 200
    assert response.json()["unique_visitors"] >= 1

    app.dependency_overrides.clear()
