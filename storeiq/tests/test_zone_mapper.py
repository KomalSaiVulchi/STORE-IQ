"""Unit tests for the zone mapper."""
# PROMPT: Write tests for ZoneMapper polygon resolution using a temporary zone_config.json file.
# CHANGES MADE: Added point-in-polygon tests for ENTRANCE, SKINCARE, and out-of-bounds coordinates.

import json
import os
import tempfile

import numpy as np

from pipeline.zone_mapper import ZoneMapper


def _create_zone_config(path: str) -> None:
    """Create a test zone config file."""
    config = {
        "zones": [
            {"zone_id": "ENTRANCE", "polygon": [[0, 0], [100, 0], [100, 100], [0, 100]]},
            {"zone_id": "SKINCARE", "polygon": [[200, 0], [400, 0], [400, 200], [200, 200]]},
            {"zone_id": "BILLING", "polygon": [[500, 500], [600, 500], [600, 600], [500, 600]]},
        ]
    }
    with open(path, "w") as f:
        json.dump(config, f)


def test_zone_resolve_inside():
    """Centroid inside a zone should return the zone ID."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _create_zone_config(f.name)
        mapper = ZoneMapper(f.name)

    result = mapper.resolve((50, 50))
    assert result == "ENTRANCE"

    result = mapper.resolve((300, 100))
    assert result == "SKINCARE"

    os.unlink(f.name)


def test_zone_resolve_outside():
    """Centroid outside all zones should return None."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _create_zone_config(f.name)
        mapper = ZoneMapper(f.name)

    result = mapper.resolve((999, 999))
    assert result is None

    os.unlink(f.name)


def test_zone_resolve_boundary():
    """Centroid on zone boundary should still resolve."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        _create_zone_config(f.name)
        mapper = ZoneMapper(f.name)

    result = mapper.resolve((0, 0))
    assert result == "ENTRANCE"

    os.unlink(f.name)
