"""Unit tests for event generation."""

from pipeline.event_generator import EventGenerator

TS = 1_000.0


def test_entry_event():
    """ENTRY event should be emitted when track enters ENTRANCE zone."""
    gen = EventGenerator("STORE_BLR_002")
    events = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="ENTRANCE", timestamp=TS
    )
    types = [e.event_type for e in events]
    assert "ENTRY" in types
    assert "ZONE_ENTER" in types

    entry_event = next(e for e in events if e.event_type == "ENTRY")
    assert entry_event.store_id == "STORE_BLR_002"
    assert entry_event.is_staff is False
    assert "session_seq" in entry_event.metadata


def test_zone_transition():
    """ZONE_EXIT and ZONE_ENTER events when moving between zones."""
    gen = EventGenerator("STORE_BLR_002")
    gen.update(track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="ENTRANCE", timestamp=TS)
    events = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="SKINCARE", timestamp=TS + 1
    )
    types = [e.event_type for e in events]
    assert "ZONE_EXIT" in types
    assert "ZONE_ENTER" in types


def test_billing_queue_join():
    """BILLING_QUEUE_JOIN event when entering BILLING zone."""
    gen = EventGenerator("STORE_BLR_002")
    gen.update(track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="ENTRANCE", timestamp=TS)
    events = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="BILLING", timestamp=TS + 1
    )
    types = [e.event_type for e in events]
    assert "BILLING_QUEUE_JOIN" in types

    join_event = next(e for e in events if e.event_type == "BILLING_QUEUE_JOIN")
    assert join_event.metadata["queue_depth"] == 1


def test_close_track_emits_zone_exit():
    """Closing a track should emit ZONE_EXIT for the last zone."""
    gen = EventGenerator("STORE_BLR_002")
    gen.update(track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="SKINCARE", timestamp=TS)
    events = gen.close_track(track_id=1, visitor_id="v1", camera_id="cam_01", timestamp=TS + 2)
    types = [e.event_type for e in events]
    assert "ZONE_EXIT" in types
    assert "EXIT" not in types


def test_no_duplicate_entry():
    """ENTRY should only be emitted once per track."""
    gen = EventGenerator("STORE_BLR_002")
    events1 = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="ENTRANCE", timestamp=TS
    )
    events2 = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="ENTRANCE", timestamp=TS + 1
    )
    entry_count = sum(1 for e in events1 + events2 if e.event_type == "ENTRY")
    assert entry_count == 1


def test_reentry_detection():
    """REENTRY event should be emitted when a visitor re-enters via line crossing."""
    gen = EventGenerator("STORE_BLR_002", is_entry_camera=True)
    gen.update(
        track_id=1,
        visitor_id="v1",
        camera_id="CAM_ENTRY_01",
        zone_id="ENTRANCE",
        timestamp=TS,
        entry_cross="ENTRY",
    )
    gen.update(
        track_id=1,
        visitor_id="v1",
        camera_id="CAM_ENTRY_01",
        zone_id="ENTRANCE",
        timestamp=TS + 1,
        entry_cross="EXIT",
    )
    events = gen.update(
        track_id=2,
        visitor_id="v1",
        camera_id="CAM_ENTRY_01",
        zone_id="ENTRANCE",
        timestamp=TS + 2,
        entry_cross="ENTRY",
    )
    types = [e.event_type for e in events]
    assert "REENTRY" in types


def test_dwell_event():
    """ZONE_DWELL should be emitted after 30 seconds."""
    gen = EventGenerator("STORE_BLR_002")
    gen.update(track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="SKINCARE", timestamp=TS)

    events = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="SKINCARE", timestamp=TS + 10
    )
    assert "ZONE_DWELL" not in [e.event_type for e in events]

    events = gen.update(
        track_id=1, visitor_id="v1", camera_id="cam_01", zone_id="SKINCARE", timestamp=TS + 31
    )
    types = [e.event_type for e in events]
    assert "ZONE_DWELL" in types

    dwell_event = next(e for e in events if e.event_type == "ZONE_DWELL")
    assert dwell_event.dwell_ms >= 30000


def test_is_staff_propagation():
    """is_staff flag should be propagated to events."""
    gen = EventGenerator("STORE_BLR_002")
    events = gen.update(
        track_id=1,
        visitor_id="v1",
        camera_id="cam_01",
        zone_id="ENTRANCE",
        timestamp=TS,
        is_staff=True,
        confidence=0.95,
    )
    for event in events:
        assert event.is_staff is True
        assert event.confidence == 0.95
