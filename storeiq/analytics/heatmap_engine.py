"""Zone heatmap analytics."""

from __future__ import annotations

from typing import Dict


class HeatmapEngine:
    """Normalize zone scores for display."""

    def normalize(self, scores: Dict[str, float]) -> Dict[str, int]:
        """Normalize scores to a 0-100 integer range."""
        if not scores:
            return {"SKINCARE": 0, "MAKEUP": 0, "HAIRCARE": 0, "BILLING": 0, "ENTRANCE": 0}
        normalized = {key: int(round(value)) for key, value in scores.items()}
        for zone in ["SKINCARE", "MAKEUP", "HAIRCARE", "BILLING", "ENTRANCE"]:
            normalized.setdefault(zone, 0)
        return normalized
