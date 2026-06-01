"""Entry/exit line-crossing detection for the entrance camera."""

from __future__ import annotations

from typing import Dict, Optional


class EntryLineDetector:
    """Detect inbound (ENTRY) and outbound (EXIT) crossings on a horizontal threshold line.

    Inbound: centroid moves from above the line to below (entering the store).
    Outbound: centroid moves from below the line to above (leaving the store).
    """

    def __init__(self, line_y: int = 520) -> None:
        self.line_y = line_y
        self._prev_y: Dict[int, int] = {}

    def update(self, track_id: int, cy: int) -> Optional[str]:
        """Return ENTRY, EXIT, or None based on line crossing."""
        prev_y = self._prev_y.get(track_id)
        self._prev_y[track_id] = cy
        if prev_y is None:
            return None
        if prev_y < self.line_y <= cy:
            return "ENTRY"
        if prev_y >= self.line_y > cy:
            return "EXIT"
        return None

    def clear(self, track_id: int) -> None:
        """Remove track state when track expires."""
        self._prev_y.pop(track_id, None)
