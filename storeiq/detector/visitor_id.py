"""Visitor ID helpers — spec format VIS_<hex>."""

from __future__ import annotations

import uuid


def new_visitor_id() -> str:
    """Generate a visitor token matching the problem statement format."""
    return f"VIS_{uuid.uuid4().hex[:6]}"


def normalize_visitor_id(raw: str) -> str:
    """Ensure visitor_id uses VIS_ prefix."""
    if raw.startswith("VIS_"):
        return raw
    return f"VIS_{raw.replace('-', '')[:6]}"
