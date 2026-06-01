"""Queue depth forecasting engine."""

from __future__ import annotations

from typing import Dict, List

import numpy as np

from database.models import MetricsHourly


class PredictionEngine:
    """Exponential smoothing based queue prediction with variance-based confidence."""

    def forecast(self, records: List[MetricsHourly]) -> Dict[str, object]:
        """Forecast queue depth for 10 and 30 minutes."""
        series = [record.queue_depth_avg or 0 for record in records]
        current = int(series[0]) if series else 0
        forecast = self._exp_smooth(series, alpha=0.4)
        confidence = self._compute_confidence(series, forecast)

        # Recommendations based on forecast trend
        if forecast > current * 1.5:
            recommendation = "Open additional billing counter immediately — queue spike predicted"
        elif forecast > current * 1.2:
            recommendation = "Open additional billing counter in next 5 minutes"
        elif forecast < current * 0.5:
            recommendation = "Consider consolidating billing counters"
        else:
            recommendation = "Queue levels stable — continue monitoring"

        return {
            "current_queue": current,
            "forecast_10min": max(0, int(round(forecast * 1.1))),
            "forecast_30min": max(0, int(round(forecast * 0.9))),
            "confidence": confidence,
            "recommendation": recommendation,
        }

    @staticmethod
    def _exp_smooth(series: List[float], alpha: float) -> float:
        """Compute exponential smoothing forecast."""
        if not series:
            return 0.0
        forecast = series[0]
        for value in series[1:]:
            forecast = alpha * value + (1 - alpha) * forecast
        return forecast

    @staticmethod
    def _compute_confidence(series: List[float], forecast: float) -> float:
        """Compute confidence from prediction error variance.

        Uses the coefficient of variation of the residuals relative to the
        forecast value. Higher variance in historical data → lower confidence.

        Returns:
            Confidence score between 0.0 and 1.0.
        """
        if len(series) < 3:
            return 0.5  # Not enough data for reliable confidence

        arr = np.array(series, dtype=np.float64)
        residuals = arr - forecast
        std = float(np.std(residuals))
        mean_abs = max(abs(forecast), 1.0)

        # Coefficient of variation (lower = more predictable)
        cv = std / mean_abs

        # Map CV to confidence: CV=0 → 0.98, CV=1 → 0.3, CV>2 → 0.1
        confidence = max(0.1, min(0.98, 1.0 - cv * 0.7))
        return round(confidence, 2)
