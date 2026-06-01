"""Tests for event persistence and session lifecycle."""
# PROMPT: Add tests for event_processor.py covering idempotency, REENTRY sessions, and staff exclusion.
# CHANGES MADE: Tests persist_event idempotency, REENTRY flag, and staff session skip.

import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.event_processor import persist_event
from database.models import Base, Event, SessionRecord


def _session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()


def _payload(event_type: str, visitor_id: str = "VIS_abc123", is_staff: bool = False) -> dict:
    return {
        "event_id": str(uuid.uuid4()),
        "store_id": "STORE_BLR_002",
        "event_type": event_type,
        "visitor_id": visitor_id,
        "camera_id": "CAM_ENTRY_01",
        "zone_id": "ENTRANCE",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "is_staff": is_staff,
        "confidence": 0.9,
        "dwell_ms": 0,
        "metadata": {"session_seq": 1},
    }


def test_persist_event_idempotent():
    db = _session()
    payload = _payload("ENTRY")
    first = persist_event(db, payload)
    second = persist_event(db, payload)
    assert first.event_id == second.event_id
    assert db.query(Event).count() == 1


def test_reentry_session_flag():
    db = _session()
    visitor = "VIS_re001"
    persist_event(db, _payload("ENTRY", visitor))
    persist_event(db, _payload("EXIT", visitor))
    persist_event(db, _payload("REENTRY", visitor))

    sessions = db.query(SessionRecord).filter(SessionRecord.visitor_id == visitor).all()
    assert len(sessions) == 2
    assert sessions[-1].reentry is True


def test_staff_events_skip_session():
    db = _session()
    persist_event(db, _payload("ENTRY", "VIS_staff1", is_staff=True))
    assert db.query(SessionRecord).count() == 0
