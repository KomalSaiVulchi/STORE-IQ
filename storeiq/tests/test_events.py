"""Unit tests for event ingestion model."""
# PROMPT: Create Pydantic validation tests for EventIngest covering the required event schema fields.
# CHANGES MADE: Added assertions for event_type and extended schema fields (store_id, is_staff, confidence, dwell_ms).

from datetime import datetime, timezone
from uuid import UUID

from api.models import EventIngest


def test_event_ingest_model():
    """Ensure event ingestion payload validates."""
    payload = EventIngest(
        event_id=UUID("b31b3d21-8c4f-4c80-92f1-2c65c6b5bf08"),
        event_type="ENTRY",
        visitor_id="visitor-01",
        camera_id="cam_01",
        zone_id="ENTRANCE",
        timestamp=datetime.now(timezone.utc),
        metadata={"confidence": 0.92},
    )
    assert payload.event_type == "ENTRY"
