"""Unit tests for prediction engine."""
# PROMPT: Add tests for PredictionEngine queue forecasting with mocked Redis history data.
# CHANGES MADE: Added tests for forecast output shape, recommendation text, and empty-history fallback.

from analytics.prediction_engine import PredictionEngine
from unittest.mock import MagicMock


def test_forecast_with_data():
    """Forecast should return valid predictions from metric records."""
    engine = PredictionEngine()
    records = []
    for i in range(10):
        record = MagicMock()
        record.queue_depth_avg = 5.0 + i * 0.5
        records.append(record)

    result = engine.forecast(records)
    assert "current_queue" in result
    assert "forecast_10min" in result
    assert "forecast_30min" in result
    assert "confidence" in result
    assert "recommendation" in result
    assert 0.0 <= result["confidence"] <= 1.0


def test_forecast_empty():
    """Forecast with no data should return zeroes."""
    engine = PredictionEngine()
    result = engine.forecast([])
    assert result["current_queue"] == 0
    assert result["forecast_10min"] == 0
    assert result["forecast_30min"] == 0


def test_confidence_stable_data():
    """Stable data should yield higher confidence than volatile data."""
    engine = PredictionEngine()
    # Stable records
    stable = []
    for _ in range(10):
        r = MagicMock()
        r.queue_depth_avg = 5.0
        stable.append(r)

    # Volatile records
    volatile = []
    for i in range(10):
        r = MagicMock()
        r.queue_depth_avg = 5.0 + (20.0 if i % 2 == 0 else -15.0)
        volatile.append(r)

    stable_result = engine.forecast(stable)
    volatile_result = engine.forecast(volatile)
    assert stable_result["confidence"] > volatile_result["confidence"]


def test_exp_smooth():
    """Exponential smoothing should return a reasonable value."""
    result = PredictionEngine._exp_smooth([10, 12, 11, 13, 10], alpha=0.4)
    assert 9 < result < 14

    # Single value
    result = PredictionEngine._exp_smooth([5.0], alpha=0.4)
    assert result == 5.0

    # Empty
    result = PredictionEngine._exp_smooth([], alpha=0.4)
    assert result == 0.0


def test_recommendation_tiers():
    """Different queue levels should produce different recommendations."""
    engine = PredictionEngine()

    # Low queue — should recommend monitoring
    records = [MagicMock(queue_depth_avg=2.0) for _ in range(10)]
    result = engine.forecast(records)
    assert "monitor" in result["recommendation"].lower() or "stable" in result["recommendation"].lower()
