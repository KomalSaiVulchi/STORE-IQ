"""FastAPI route tests."""
# PROMPT: Please update the API tests to use the new store-scoped endpoints and test idempotency and batch ingestion.
# CHANGES MADE: Updated /metrics, /health tests. Added tests for /stores/{id}/metrics, idempotency, batch ingestion, empty store, zero purchases.

import os
from datetime import datetime, timezone
import uuid

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg2://storeiq:storeiq@localhost:5432/storeiq")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("KAFKA_BOOTSTRAP", "localhost:9092")

from fastapi.testclient import TestClient

from api.main import app
from api.db import get_db
from database.models import Event, MetricsHourly, SessionRecord, PosTransaction


class FakeQuery:
    """Simple query stub for API tests."""

    def __init__(self, result=None, count_value=0, list_value=None, scalar_value=None):
        self._result = result
        self._count = count_value
        self._list = list_value or []
        self._scalar = scalar_value

    def filter(self, *_args, **_kwargs):
        return self

    def order_by(self, *_args, **_kwargs):
        return self

    def group_by(self, *_args, **_kwargs):
        return self

    def with_entities(self, *_args, **_kwargs):
        return self

    def count(self):
        return self._count

    def first(self):
        return self._result

    def all(self):
        return self._list

    def one_or_none(self):
        return self._result

    def scalar(self):
        return self._scalar


class FakeSession:
    """Fake SQLAlchemy session for API tests."""

    def __init__(self, empty=False, zero_purchases=False):
        now = datetime.now(timezone.utc)
        self.empty = empty
        self.zero_purchases = zero_purchases

        self.metrics = MetricsHourly(
            hour_bucket=now,
            unique_visitors=245,
            avg_dwell_sec=420,
            conversion_rate=12.8,
            zone_scores={"SKINCARE": 82, "MAKEUP": 65, "HAIRCARE": 41, "BILLING": 55},
            queue_depth_avg=3,
        )
        self.event = Event(
            event_id="test",
            store_id="STORE_BLR_002",
            event_type="ENTRY",
            visitor_id="visitor",
            track_id=None,
            camera_id="cam_01",
            zone_id="ENTRANCE",
            timestamp=now,
            metadata_json={},
            is_staff=False,
            confidence=0.9,
            dwell_ms=0,
        )

        self.event_list = [self.event] if not empty else []
        self.metrics_list = [self.metrics] if not empty else []

    def query(self, *args, **kwargs):
        model = args[0] if args else None
        
        # Handle scalar queries (like func.count)
        if not hasattr(model, "__tablename__"):
             if "avg" in str(args[0]):
                  return FakeQuery(scalar_value=300 if not self.empty else 0)
             if "count" in str(args[0]):
                  return FakeQuery(scalar_value=100 if not self.empty else 0, count_value=100 if not self.empty else 0)
             
             # Group by queries (e.g. for zone counts/dwell)
             if len(args) > 1 and "zone_id" in str(args[0]):
                  if self.empty:
                      return FakeQuery(list_value=[])
                  if "avg" in str(args[1]):
                       return FakeQuery(list_value=[("SKINCARE", 300000), ("MAKEUP", 180000)])
                  else:
                       return FakeQuery(list_value=[("SKINCARE", 50), ("MAKEUP", 30)])

             # Peak hour query
             if len(args) > 1 and "date_trunc" in str(args[0]):
                  class FakeRow:
                      def __init__(self, dt):
                          self.dt = dt
                      def __getitem__(self, i):
                          return self.dt
                  
                  return FakeQuery(result=FakeRow(datetime.now(timezone.utc)) if not self.empty else None)
             
             return FakeQuery(scalar_value=50 if not self.empty else 0)

        if model is MetricsHourly:
            return FakeQuery(result=self.metrics if not self.empty else None)
        if model is SessionRecord:
            count = 0 if self.empty else (0 if self.zero_purchases else 18)
            return FakeQuery(result=None, count_value=count, scalar_value=count)
        if model is Event:
            return FakeQuery(result=self.event if not self.empty else None, count_value=5 if not self.empty else 0, list_value=self.event_list)
        if model is PosTransaction:
            return FakeQuery(list_value=[])
        return FakeQuery()

    def add(self, record):
        pass

    def commit(self):
        pass

    def rollback(self):
        pass

    def close(self):
        return None


def override_get_db():
    """Override DB dependency for tests."""
    yield FakeSession()

def override_get_db_empty():
    yield FakeSession(empty=True)

def override_get_db_zero_purchases():
    yield FakeSession(zero_purchases=True)


app.dependency_overrides[get_db] = override_get_db

import time
from api.main import InMemoryRedis
app.state.redis = InMemoryRedis()
app.state.kafka_producer = None
app.state.started_at = time.time()

client = TestClient(app)


def test_metrics_endpoint():
    """GET /stores/{store_id}/metrics should return payload."""
    from unittest.mock import patch
    from api.models import MetricsResponse

    mock_metrics = MetricsResponse(
        unique_visitors=245,
        current_in_store=18,
        avg_dwell_minutes=7.4,
        conversion_rate=12.8,
        queue_depth=3,
        abandonment_rate=8.5,
        peak_hour="18:00",
        zone_scores={"SKINCARE": 82, "MAKEUP": 65},
        avg_dwell_per_zone={"SKINCARE": 5.2},
    )
    with patch("api.routers.metrics.compute_store_metrics", return_value=mock_metrics):
        response = client.get("/stores/STORE_BLR_002/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["unique_visitors"] == 245


def test_empty_store_metrics():
    """Metrics should handle empty store data gracefully."""
    app.dependency_overrides[get_db] = override_get_db_empty
    response = client.get("/stores/STORE_BLR_002/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["unique_visitors"] == 0
    assert payload["conversion_rate"] == 0.0
    app.dependency_overrides[get_db] = override_get_db


def test_zero_purchases_metrics():
    """Metrics should handle stores with no purchases gracefully."""
    app.dependency_overrides[get_db] = override_get_db_zero_purchases
    response = client.get("/stores/STORE_BLR_002/metrics")
    assert response.status_code == 200
    payload = response.json()
    assert payload["conversion_rate"] == 0.0
    app.dependency_overrides[get_db] = override_get_db


def test_health_endpoint():
    """GET /health should return healthy status and store details."""
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] in {"healthy", "degraded"}
    assert "stores" in payload


def test_event_ingest_idempotency():
    """POST /events/ingest should be idempotent."""
    from unittest.mock import MagicMock, patch

    event_id = str(uuid.uuid4())
    payload = {
        "event_id": event_id,
        "store_id": "STORE_BLR_002",
        "event_type": "ENTRY",
        "visitor_id": "v1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }

    with patch("api.routers.events.persist_event") as mock_persist:
        mock_persist.return_value = MagicMock(event_id=event_id)
        response1 = client.post("/events/ingest", json=payload)
        assert response1.status_code == 200
        response2 = client.post("/events/ingest", json=payload)
        assert response2.status_code == 200
        assert mock_persist.call_count == 2


def test_batch_ingest_on_main_endpoint():
    """POST /events/ingest should accept a batch payload on the main endpoint."""
    from unittest.mock import MagicMock, patch

    payload = {
        "events": [
            {
                "event_id": str(uuid.uuid4()),
                "store_id": "STORE_BLR_002",
                "event_type": "ENTRY",
                "visitor_id": "v1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": str(uuid.uuid4()),
                "store_id": "STORE_BLR_002",
                "event_type": "ZONE_ENTER",
                "visitor_id": "v1",
                "zone_id": "SKINCARE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]
    }
    with patch("api.routers.events.persist_event") as mock_persist:
        mock_persist.return_value = MagicMock()
        response = client.post("/events/ingest", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 2
    assert data["rejected"] == 0


def test_batch_ingest():
    """POST /events/ingest/batch should accept multiple events."""
    from unittest.mock import MagicMock, patch

    payload = {
        "events": [
            {
                "event_id": str(uuid.uuid4()),
                "store_id": "STORE_BLR_002",
                "event_type": "ENTRY",
                "visitor_id": "v1",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
            {
                "event_id": str(uuid.uuid4()),
                "store_id": "STORE_BLR_002",
                "event_type": "ZONE_ENTER",
                "visitor_id": "v1",
                "zone_id": "SKINCARE",
                "timestamp": datetime.now(timezone.utc).isoformat(),
            },
        ]
    }
    with patch("api.routers.events.persist_event") as mock_persist:
        mock_persist.return_value = MagicMock()
        response = client.post("/events/ingest/batch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["accepted"] == 2
    assert data["rejected"] == 0
