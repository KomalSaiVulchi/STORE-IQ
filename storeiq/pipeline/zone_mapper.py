"""Polygon ROI zone mapping — per-camera configurations."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class Zone:
    """Zone definition."""

    zone_id: str
    polygon: np.ndarray


class ZoneMapper:
    """Resolve centroid positions to named zones for a specific camera."""

    def __init__(self, config_path: str, camera_id: Optional[str] = None) -> None:
        """Load zone polygons from configuration."""
        with open(config_path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)

        zone_defs: List[dict] = []
        self.entry_line_y: Optional[int] = None

        cameras = payload.get("cameras", {})
        if camera_id and camera_id in cameras:
            cam_cfg = cameras[camera_id]
            zone_defs = cam_cfg.get("zones", [])
            self.entry_line_y = cam_cfg.get("entry_line_y")
        elif payload.get("zones"):
            zone_defs = payload["zones"]
        else:
            zone_defs = payload.get("default_zones", [])

        self.zones = [
            Zone(zone_id=zone["zone_id"], polygon=np.array(zone["polygon"], dtype=np.int32))
            for zone in zone_defs
        ]

    @classmethod
    def for_camera(cls, config_path: str, camera_id: str) -> ZoneMapper:
        """Create a mapper scoped to one camera."""
        return cls(config_path, camera_id=camera_id)

    def resolve(self, centroid: Tuple[int, int]) -> Optional[str]:
        """Return the zone id for a centroid or None."""
        point = (int(centroid[0]), int(centroid[1]))
        for zone in self.zones:
            if cv2.pointPolygonTest(zone.polygon, point, False) >= 0:
                return zone.zone_id
        return None
