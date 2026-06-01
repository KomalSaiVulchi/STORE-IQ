"""Prediction API router."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.models import QueuePredictionResponse
from api.db import get_db
from analytics.prediction_engine import PredictionEngine
from database.models import MetricsHourly


router = APIRouter()


def _forecast(db: Session) -> QueuePredictionResponse:
    records = db.query(MetricsHourly).order_by(MetricsHourly.hour_bucket.desc()).limit(24).all()
    engine = PredictionEngine()
    prediction = engine.forecast(records)
    return QueuePredictionResponse(**prediction)


@router.get("/stores/{store_id}/predict/queue", response_model=QueuePredictionResponse)
async def predict_store_queue(store_id: str, db: Session = Depends(get_db)) -> QueuePredictionResponse:
    """Return queue depth predictions for a store."""
    return _forecast(db)


@router.get("/predict/queue", response_model=QueuePredictionResponse)
async def predict_queue(db: Session = Depends(get_db)) -> QueuePredictionResponse:
    """Return queue depth predictions — legacy endpoint."""
    return _forecast(db)
