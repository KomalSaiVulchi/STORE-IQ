"""Persist visitor feature vectors."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict

from sqlalchemy.orm import Session

from database.models import VisitorFeature


class FeatureWriter:
    """Persist per-visitor features when sessions close."""

    def upsert(self, db: Session, visitor_id: str, features: Dict[str, object]) -> None:
        """Insert or update visitor features."""
        record = db.query(VisitorFeature).filter(VisitorFeature.visitor_id == visitor_id).one_or_none()
        if record is None:
            record = VisitorFeature(visitor_id=visitor_id)
            db.add(record)
        record.avg_dwell_sec = float(features.get("avg_dwell_sec", 0))
        record.visit_count = int(features.get("visit_count", 0))
        record.zone_affinity = features.get("zone_affinity", {})
        record.billing_rate = float(features.get("billing_rate", 0))
        record.conversion_rate = float(features.get("conversion_rate", 0))
        record.last_seen = datetime.now(timezone.utc)
        db.commit()
