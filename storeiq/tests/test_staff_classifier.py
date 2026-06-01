"""Tests for staff uniform classification."""
# PROMPT: Add unit tests for staff_classifier.py using synthetic uniform-colored crops.
# CHANGES MADE: Tests dark uniform detection and customer-like bright clothing.

import numpy as np

from detector.staff_classifier import classify_staff


def test_staff_dark_uniform():
    """Dark upper-body crop should classify as staff."""
    frame = np.zeros((200, 100, 3), dtype=np.uint8)
    frame[0:80, :] = (20, 20, 40)  # dark navy uniform
    is_staff, confidence = classify_staff(frame, (10, 10, 90, 180))
    assert is_staff is True
    assert confidence > 0.5


def test_customer_bright_clothing():
    """Bright clothing should not classify as staff."""
    frame = np.full((200, 100, 3), 220, dtype=np.uint8)
    is_staff, confidence = classify_staff(frame, (10, 10, 90, 180))
    assert is_staff is False
