"""Event generation for tracked visitors — full schema compliance."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class GeneratedEvent:
    """Event emitted from the tracking pipeline — matches problem statement schema."""

    event_id: str
    store_id: str
    event_type: str
    visitor_id: str
    track_id: int
    camera_id: str
    zone_id: Optional[str]
    timestamp: float
    is_staff: bool
    confidence: float
    dwell_ms: int
    metadata: dict


class EventGenerator:
    """Generate events based on track state and zone transitions."""

    DWELL_THRESHOLD_SEC = 30

    def __init__(self, store_id: Optional[str] = None, is_entry_camera: bool = False) -> None:
        self._store_id = store_id or os.getenv("STORE_ID", "STORE_BLR_002")
        self._is_entry_camera = is_entry_camera
        self._last_zone: Dict[int, Optional[str]] = {}
        self._zone_enter_time: Dict[int, float] = {}
        self._entry_emitted: Dict[int, bool] = {}
        self._exit_emitted: Dict[int, bool] = {}
        self._last_exit_by_visitor: Dict[str, float] = {}
        self._session_seq: Dict[str, int] = {}
        self._queue_depth: int = 0
        self._billing_enter_time: Dict[int, float] = {}

    def update(
        self,
        track_id: int,
        visitor_id: str,
        camera_id: str,
        zone_id: Optional[str],
        timestamp: float,
        confidence: float = 0.0,
        is_staff: bool = False,
        entry_cross: Optional[str] = None,
    ) -> List[GeneratedEvent]:
        """Generate events for a single track update."""
        events: List[GeneratedEvent] = []
        now = timestamp
        previous = self._last_zone.get(track_id)

        if visitor_id not in self._session_seq:
            self._session_seq[visitor_id] = 0

        # Entry camera: ENTRY/EXIT from line crossing only
        if entry_cross == "ENTRY" and not self._entry_emitted.get(track_id):
            events.append(
                self._make_event("ENTRY", visitor_id, track_id, camera_id, "ENTRANCE", now, confidence, is_staff)
            )
            if visitor_id in self._last_exit_by_visitor:
                events.append(
                    self._make_event("REENTRY", visitor_id, track_id, camera_id, "ENTRANCE", now, confidence, is_staff)
                )
            self._entry_emitted[track_id] = True
            self._exit_emitted[track_id] = False

        if entry_cross == "EXIT" and not self._exit_emitted.get(track_id):
            events.append(
                self._make_event("EXIT", visitor_id, track_id, camera_id, "ENTRANCE", now, confidence, is_staff)
            )
            self._last_exit_by_visitor[visitor_id] = now
            self._exit_emitted[track_id] = True
            self._entry_emitted[track_id] = False

        if previous != zone_id:
            if previous:
                events.append(
                    self._make_event("ZONE_EXIT", visitor_id, track_id, camera_id, previous, now, confidence, is_staff)
                )
                if previous == "BILLING":
                    self._queue_depth = max(0, self._queue_depth - 1)
                    billing_enter = self._billing_enter_time.get(track_id, now)
                    if now - billing_enter < 30:
                        events.append(
                            self._make_event(
                                "BILLING_QUEUE_ABANDON",
                                visitor_id,
                                track_id,
                                camera_id,
                                previous,
                                now,
                                confidence,
                                is_staff,
                            )
                        )
            if zone_id:
                events.append(
                    self._make_event("ZONE_ENTER", visitor_id, track_id, camera_id, zone_id, now, confidence, is_staff)
                )
                self._zone_enter_time[track_id] = now
                if zone_id == "BILLING":
                    self._billing_enter_time[track_id] = now
        else:
            if zone_id:
                enter_time = self._zone_enter_time.get(track_id, now)
                dwell_elapsed = now - enter_time
                if dwell_elapsed >= self.DWELL_THRESHOLD_SEC:
                    dwell_ms = int(dwell_elapsed * 1000)
                    events.append(
                        self._make_event(
                            "ZONE_DWELL",
                            visitor_id,
                            track_id,
                            camera_id,
                            zone_id,
                            now,
                            confidence,
                            is_staff,
                            dwell_ms=dwell_ms,
                        )
                    )
                    self._zone_enter_time[track_id] = now

        self._last_zone[track_id] = zone_id

        # Non-entry cameras: zone-based ENTRY only when entering ENTRANCE polygon (rare)
        if (
            not self._is_entry_camera
            and zone_id == "ENTRANCE"
            and not self._entry_emitted.get(track_id)
        ):
            events.append(
                self._make_event("ENTRY", visitor_id, track_id, camera_id, zone_id, now, confidence, is_staff)
            )
            self._entry_emitted[track_id] = True

        if zone_id == "BILLING" and previous != "BILLING":
            self._queue_depth += 1
            events.append(
                self._make_event(
                    "BILLING_QUEUE_JOIN",
                    visitor_id,
                    track_id,
                    camera_id,
                    zone_id,
                    now,
                    confidence,
                    is_staff,
                    queue_depth=self._queue_depth,
                )
            )

        return events

    def close_track(
        self,
        track_id: int,
        visitor_id: str,
        camera_id: str,
        timestamp: float,
        confidence: float = 0.0,
        is_staff: bool = False,
    ) -> List[GeneratedEvent]:
        """Emit zone exit when a track disappears (not store EXIT on entry camera)."""
        now = timestamp
        previous = self._last_zone.get(track_id)
        events: List[GeneratedEvent] = []

        if previous:
            events.append(
                self._make_event("ZONE_EXIT", visitor_id, track_id, camera_id, previous, now, confidence, is_staff)
            )
            if previous == "BILLING":
                self._queue_depth = max(0, self._queue_depth - 1)

        self._last_zone.pop(track_id, None)
        self._zone_enter_time.pop(track_id, None)
        self._billing_enter_time.pop(track_id, None)
        self._entry_emitted.pop(track_id, None)
        self._exit_emitted.pop(track_id, None)
        return events

    def _make_event(
        self,
        event_type: str,
        visitor_id: str,
        track_id: int,
        camera_id: str,
        zone_id: Optional[str],
        timestamp: float,
        confidence: float = 0.0,
        is_staff: bool = False,
        dwell_ms: int = 0,
        queue_depth: Optional[int] = None,
    ) -> GeneratedEvent:
        self._session_seq.setdefault(visitor_id, 0)
        self._session_seq[visitor_id] += 1

        metadata = {
            "queue_depth": queue_depth,
            "sku_zone": zone_id if zone_id and zone_id not in ("ENTRANCE", "BILLING") else None,
            "session_seq": self._session_seq[visitor_id],
        }

        return GeneratedEvent(
            event_id=str(uuid.uuid4()),
            store_id=self._store_id,
            event_type=event_type,
            visitor_id=visitor_id,
            track_id=track_id,
            camera_id=camera_id,
            zone_id=zone_id,
            timestamp=timestamp,
            is_staff=is_staff,
            confidence=confidence,
            dwell_ms=dwell_ms,
            metadata=metadata,
        )
