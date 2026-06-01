"""Visitor session lifecycle management."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional

from sqlalchemy.orm import Session

from database.models import SessionRecord


@dataclass
class SessionState:
    """In-memory session state for a visitor."""

    session_id: str
    visitor_id: str
    entry_time: datetime
    zones_visited: List[str] = field(default_factory=list)
    billing_visited: bool = False
    purchase: bool = False
    reentry: bool = False
    camera_path: List[str] = field(default_factory=list)


class SessionEngine:
    """Manage session lifecycle and persist to the database."""

    def __init__(self) -> None:
        """Initialize session cache."""
        self._sessions: Dict[str, SessionState] = {}

    def open_session(self, visitor_id: str, camera_id: str, db: Session) -> SessionState:
        """Open a new session for a visitor."""
        session_id = str(uuid.uuid4())
        state = SessionState(session_id=session_id, visitor_id=visitor_id, entry_time=datetime.now(timezone.utc))
        state.camera_path.append(camera_id)
        self._sessions[visitor_id] = state
        record = SessionRecord(
            session_id=session_id,
            visitor_id=visitor_id,
            entry_time=state.entry_time,
            zones_visited=state.zones_visited,
            billing_visited=False,
            purchase=False,
            dwell_seconds=0,
            reentry=False,
            camera_path=state.camera_path,
        )
        db.add(record)
        db.commit()
        return state

    def update_zone(self, visitor_id: str, zone_id: str, db: Session) -> None:
        """Update session with a new zone visit."""
        state = self._sessions.get(visitor_id)
        if not state:
            return
        if zone_id not in state.zones_visited:
            state.zones_visited.append(zone_id)
        record = db.query(SessionRecord).filter(SessionRecord.session_id == state.session_id).one_or_none()
        if record:
            record.zones_visited = state.zones_visited
            if zone_id == "BILLING":
                record.billing_visited = True
            db.commit()

    def close_session(self, visitor_id: str, db: Session) -> Optional[SessionRecord]:
        """Close a session for a visitor and persist dwell time."""
        state = self._sessions.pop(visitor_id, None)
        if not state:
            return None
        now = datetime.now(timezone.utc)
        record = db.query(SessionRecord).filter(SessionRecord.session_id == state.session_id).one_or_none()
        if record:
            record.exit_time = now
            record.dwell_seconds = int((now - state.entry_time).total_seconds())
            db.commit()
        return record
