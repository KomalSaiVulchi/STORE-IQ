"""Video ingestion for RTSP or file streams."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Generator, Tuple, Union

import cv2
import numpy as np


def ensure_sample_video(path: str, width: int = 640, height: int = 360) -> None:
    """Create a short synthetic mp4 file if one is missing."""
    if os.path.exists(path):
        return
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(path, fourcc, 10.0, (width, height))
    for i in range(60):
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        cv2.rectangle(frame, (30 + i * 3, 60), (120 + i * 3, 260), (0, 255, 0), -1)
        writer.write(frame)
    writer.release()


def stream_frames(
    source: str,
    clip_start: str = "2026-04-10T10:00:00+00:00",
) -> Generator[Tuple[np.ndarray, float], None, None]:
    """Yield frames and UTC epoch timestamps derived from clip offset.

    Timestamps follow the problem statement: ISO-8601 UTC from clip start + frame offset.
    """
    if source.endswith(".mp4"):
        ensure_sample_video(source)
    cap = cv2.VideoCapture(source)
    if not cap.isOpened():
        raise RuntimeError(f"Unable to open video source: {source}")

    fps = cap.get(cv2.CAP_PROP_FPS) or 15.0
    start_dt = datetime.fromisoformat(clip_start.replace("Z", "+00:00"))
    if start_dt.tzinfo is None:
        start_dt = start_dt.replace(tzinfo=timezone.utc)

    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        ts = start_dt + timedelta(seconds=frame_idx / fps)
        frame_idx += 1
        yield frame, ts.timestamp()
    cap.release()


def event_to_payload(event) -> dict:
    """Serialize a GeneratedEvent dataclass to an ingest-compatible dict."""
    ts = event.timestamp
    if isinstance(ts, (int, float)):
        timestamp = datetime.fromtimestamp(ts, tz=timezone.utc).isoformat().replace("+00:00", "Z")
    else:
        timestamp = ts.isoformat().replace("+00:00", "Z")

    return {
        "event_id": event.event_id,
        "store_id": event.store_id,
        "event_type": event.event_type,
        "visitor_id": event.visitor_id,
        "track_id": event.track_id,
        "camera_id": event.camera_id,
        "zone_id": event.zone_id,
        "timestamp": timestamp,
        "is_staff": event.is_staff,
        "confidence": event.confidence,
        "dwell_ms": event.dwell_ms,
        "metadata": event.metadata,
    }
