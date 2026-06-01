"""Heuristic staff uniform detection from upper-body crop colors."""

from __future__ import annotations

from typing import Tuple

import cv2
import numpy as np


def classify_staff(frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> tuple[bool, float]:
    """Classify whether a person is store staff based on uniform-like colors.

    Purplle store staff typically wear dark branded uniforms (black/navy/purple).
    We analyse the upper-third of the bounding box in HSV space.

    Returns:
        (is_staff, confidence)
    """
    x1, y1, x2, y2 = bbox
    h, w = frame.shape[:2]
    x1, y1 = max(0, x1), max(0, y1)
    x2, y2 = min(w, x2), min(h, y2)
    if x2 <= x1 or y2 <= y1:
        return False, 0.0

    crop_h = max(1, int((y2 - y1) * 0.45))
    upper = frame[y1 : y1 + crop_h, x1:x2]
    if upper.size == 0:
        return False, 0.0

    hsv = cv2.cvtColor(upper, cv2.COLOR_BGR2HSV)
    # Dark uniform: low value, moderate saturation (not grey noise)
    dark_mask = hsv[:, :, 2] < 90
    # Purple/navy brand tones
    purple_mask = cv2.inRange(hsv, np.array([120, 30, 20]), np.array([165, 255, 120]))
    navy_mask = cv2.inRange(hsv, np.array([100, 40, 15]), np.array([130, 255, 100]))

    total = upper.shape[0] * upper.shape[1]
    dark_ratio = float(np.count_nonzero(dark_mask)) / total
    purple_ratio = float(np.count_nonzero(purple_mask)) / total
    navy_ratio = float(np.count_nonzero(navy_mask)) / total

    uniform_score = max(dark_ratio * 0.6 + purple_ratio * 0.25 + navy_ratio * 0.25, dark_ratio)
    is_staff = uniform_score >= 0.55
    confidence = min(0.98, round(uniform_score, 2))
    return is_staff, confidence if is_staff else round(1.0 - uniform_score, 2)
