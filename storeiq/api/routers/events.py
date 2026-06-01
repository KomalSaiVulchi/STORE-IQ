"""Event ingestion API router — unified via event_processor."""

import logging
from typing import List, Union

from api.rate_limit import limiter
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import TypeAdapter, ValidationError
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from api.config import get_settings
from api.db import get_db
from api.event_processor import persist_event
from api.models import (
    BatchIngestRequest,
    BatchIngestResponse,
    BatchIngestResult,
    EventAccepted,
    EventIngest,
)


router = APIRouter()
settings = get_settings()
logger = logging.getLogger("storeiq-api")
_event_list_adapter = TypeAdapter(List[EventIngest])


def _event_to_payload(event: EventIngest) -> dict:
    """Convert Pydantic model to persist_event dict."""
    data = event.model_dump(mode="json")
    data["event_id"] = str(event.event_id)
    return data


def _touch_redis(request: Request, event: EventIngest) -> None:
    """Update last-event timestamps in Redis for health checks."""
    ts = event.timestamp.isoformat()
    request.app.state.redis.set("last_event_ts", ts)
    request.app.state.redis.set(f"last_event_ts:{event.store_id}", ts)


async def _publish_kafka(request: Request, payload: dict) -> None:
    """Publish accepted event to Kafka if producer is available."""
    producer = request.app.state.kafka_producer
    if not producer:
        return
    try:
        await producer.send(settings.kafka_raw_topic, payload)
    except Exception as exc:
        logger.warning(
            {
                "trace_id": getattr(request.state, "trace_id", "unknown"),
                "store_id": payload.get("store_id"),
                "event_type": payload.get("event_type"),
                "message": "Kafka publish failed",
                "error": str(exc),
            }
        )


def _ingest_one(event: EventIngest, request: Request, db: Session) -> BatchIngestResult:
    """Persist one event through the shared processor (sessions + idempotency)."""
    payload = _event_to_payload(event)
    persist_event(db, payload)
    _touch_redis(request, event)
    return BatchIngestResult(event_id=str(event.event_id), status="accepted")


@router.post(
    "/events/ingest",
    response_model=Union[EventAccepted, BatchIngestResponse],
)
@limiter.limit("120/minute")
async def ingest_events(request: Request, db: Session = Depends(get_db)):
    """Ingest one or up to 500 events with idempotency and partial success."""
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=422, content={"detail": "Invalid JSON payload"})

    try:
        if isinstance(body, list):
            events = _event_list_adapter.validate_python(body)
        elif isinstance(body, dict) and "events" in body:
            events = BatchIngestRequest.model_validate(body).events
        else:
            events = [EventIngest.model_validate(body)]
    except ValidationError as exc:
        return JSONResponse(status_code=422, content={"detail": exc.errors()})

    if len(events) > 500:
        return JSONResponse(
            status_code=422,
            content={"detail": "Batch size exceeds maximum of 500 events"},
        )

    try:
        if len(events) == 1:
            result = _ingest_one(events[0], request, db)
            await _publish_kafka(request, _event_to_payload(events[0]))
            return EventAccepted(status="accepted", event_id=result.event_id)

        results: list[BatchIngestResult] = []
        accepted = 0
        rejected = 0
        for event in events:
            try:
                results.append(_ingest_one(event, request, db))
                await _publish_kafka(request, _event_to_payload(event))
                accepted += 1
            except OperationalError:
                raise
            except Exception as exc:
                db.rollback()
                results.append(
                    BatchIngestResult(
                        event_id=str(event.event_id),
                        status="rejected",
                        error=str(exc),
                    )
                )
                rejected += 1

        return BatchIngestResponse(accepted=accepted, rejected=rejected, results=results)

    except OperationalError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry."},
        )


@router.post("/events/ingest/batch", response_model=BatchIngestResponse)
@limiter.limit("120/minute")
async def ingest_batch(
    payload: BatchIngestRequest,
    request: Request,
    db: Session = Depends(get_db),
) -> BatchIngestResponse:
    """Legacy batch endpoint — delegates to unified ingest logic."""
    try:
        results: list[BatchIngestResult] = []
        accepted = 0
        rejected = 0
        for event in payload.events:
            try:
                results.append(_ingest_one(event, request, db))
                await _publish_kafka(request, _event_to_payload(event))
                accepted += 1
            except OperationalError:
                return JSONResponse(
                    status_code=503,
                    content={"detail": "Database temporarily unavailable. Please retry."},
                )
            except Exception as exc:
                db.rollback()
                results.append(
                    BatchIngestResult(
                        event_id=str(event.event_id),
                        status="rejected",
                        error=str(exc),
                    )
                )
                rejected += 1
        return BatchIngestResponse(accepted=accepted, rejected=rejected, results=results)
    except OperationalError:
        return JSONResponse(
            status_code=503,
            content={"detail": "Database temporarily unavailable. Please retry."},
        )
