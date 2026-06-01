"""Footfall analytics engine."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from database.models import MetricsHourly


class FootfallEngine:
    """Compute footfall metrics."""

    def unique_visitors(self, latest: MetricsHourly | None) -> int:
        """Return unique visitor count from the latest metrics row."""
        if not latest or latest.unique_visitors is None:
            return 0
        return int(latest.unique_visitors)

    def peak_hour(self, db: Session) -> str:
        """Return the hour bucket with highest unique visitors."""
        record = db.query(MetricsHourly).order_by(MetricsHourly.unique_visitors.desc()).first()
        if not record:
            return "--:--"
        return record.hour_bucket.strftime("%H:00")
