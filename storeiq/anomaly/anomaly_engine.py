"""Z-score based anomaly detection engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

import numpy as np


@dataclass
class AnomalyResult:
    """Anomaly computation result."""

    type: str
    severity: str
    confidence: float
    reason: str
    zone_id: str | None = None


class AnomalyEngine:
    """Compute z-score based anomalies for queue, conversion, and zone visits."""

    def queue_spike(self, current: float, baseline: List[float]) -> AnomalyResult | None:
        """Detect queue depth spike anomalies."""
        z = self._z_score(current, baseline)
        if z > 3.5:
            return self._result("QUEUE_SPIKE", "CRITICAL", z, "Queue depth 3.5σ above baseline")
        if z > 2.0:
            return self._result("QUEUE_SPIKE", "WARN", z, "Queue depth 2σ above baseline")
        return None

    def conversion_drop(self, current: float, weekly_avg: float) -> AnomalyResult | None:
        """Detect conversion drops."""
        if weekly_avg <= 0:
            return None
        ratio = current / weekly_avg
        if ratio < 0.5:
            return self._result("CONVERSION_DROP", "CRITICAL", 0.9, "Conversion rate below 50% of weekly average")
        if ratio < 0.7:
            return self._result("CONVERSION_DROP", "WARN", 0.7, "Conversion rate below 70% of weekly average")
        return None

    def dead_zone(self, zone_visits: int, minutes: int, zone_id: str) -> AnomalyResult | None:
        """Detect dead zone anomalies."""
        if zone_visits == 0 and minutes >= 60:
            return self._result("DEAD_ZONE", "CRITICAL", 0.95, "Zone has zero visits for 60 minutes", zone_id)
        if zone_visits == 0 and minutes >= 30:
            return self._result("DEAD_ZONE", "WARN", 0.7, "Zone has zero visits for 30 minutes", zone_id)
        return None

    def camera_offline(self, minutes: int, camera_id: str) -> AnomalyResult | None:
        """Detect camera offline anomalies."""
        if minutes > 10:
            return self._result("CAMERA_OFFLINE", "CRITICAL", 0.95, f"Camera {camera_id} offline for 10 minutes")
        return None

    def crowd_alert(self, current: int, capacity: int) -> AnomalyResult | None:
        """Detect crowd alerts for store capacity."""
        if current > capacity * 0.95:
            return self._result("CROWD_ALERT", "CRITICAL", 0.9, "Store occupancy above 95% capacity")
        if current > capacity * 0.85:
            return self._result("CROWD_ALERT", "WARN", 0.7, "Store occupancy above 85% capacity")
        return None

    @staticmethod
    def _z_score(current: float, baseline: List[float]) -> float:
        """Compute z-score given baseline samples."""
        if not baseline:
            return 0.0
        mean = float(np.mean(baseline))
        std = float(np.std(baseline)) or 1.0
        return (current - mean) / std

    @staticmethod
    def _result(name: str, severity: str, z: float, reason: str, zone_id: str | None = None) -> AnomalyResult:
        """Construct an anomaly result."""
        confidence = min(1.0, abs(z) / 4) if z else 0.8
        return AnomalyResult(type=name, severity=severity, confidence=confidence, reason=reason, zone_id=zone_id)
