"""YOLOv11 person detector wrapper."""

from __future__ import annotations

import os
import random
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
from ultralytics import YOLO

from detector.staff_classifier import classify_staff


@dataclass
class Detection:
    """Detection result for a single person."""

    bbox: Tuple[int, int, int, int]
    confidence: float
    is_staff: bool = False


class YoloDetector:
    """A lightweight wrapper for YOLOv11 person detection.

    This implementation supports a mock mode for environments without model weights.
    """

    def __init__(self) -> None:
        """Initialize the detector and determine mock mode."""
        self.use_mock = os.getenv("USE_MOCK_DETECTION", "false").lower() == "true"
        self._model = None
        if not self.use_mock:
            model_name = os.getenv("YOLO_MODEL", "yolov8n.pt")
            self._model = YOLO(model_name)  # downloads weights on first run

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """Run person detection on a frame.

        Args:
            frame: BGR image array.

        Returns:
            A list of Detection results for class=person.
        """
        if self.use_mock:
            return self._mock_detect(frame)
        return self._yolo_detect(frame)

    def _yolo_detect(self, frame: np.ndarray) -> List[Detection]:
        """Run YOLOv11 detection using pretrained weights."""
        if not self._model:
            return self._mock_detect(frame)
        rgb = frame[:, :, ::-1]
        results = self._model.predict(rgb, conf=0.5, classes=[0], verbose=False)
        detections: List[Detection] = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                detections.append(
                    Detection(
                        bbox=(int(x1), int(y1), int(x2), int(y2)),
                        confidence=float(box.conf.item()),
                        is_staff=classify_staff(frame, (int(x1), int(y1), int(x2), int(y2)))[0],
                    )
                )
        return detections

    def _mock_detect(self, frame: np.ndarray) -> List[Detection]:
        """Generate deterministic mock detections for testing pipelines."""
        height, width = frame.shape[:2]
        random.seed(width + height)
        detections: List[Detection] = []
        for _ in range(random.randint(1, 3)):
            x1 = random.randint(0, max(1, width - 120))
            y1 = random.randint(0, max(1, height - 180))
            x2 = min(width, x1 + random.randint(60, 120))
            y2 = min(height, y1 + random.randint(120, 220))
            is_staff, _ = classify_staff(frame, (x1, y1, x2, y2))
            detections.append(Detection(bbox=(x1, y1, x2, y2), confidence=0.75, is_staff=is_staff))
        return detections
