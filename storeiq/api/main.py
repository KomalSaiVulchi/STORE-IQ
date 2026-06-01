"""FastAPI application entrypoint."""

from __future__ import annotations

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Dict

import redis
from fastapi import FastAPI, Request, Response, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy.exc import OperationalError
from api.db import engine

from api.config import get_settings
from api.rate_limit import limiter
from api.middleware import configure_logger, logging_middleware
from api.websocket import ConnectionManager, periodic_broadcast
from api.routers import anomalies, events, funnel, heatmap, health, metrics, predict
from database.models import Base
from streaming.kafka_producer import KafkaProducerClient


# Metrics are defined in api.middleware and registered globally

settings = get_settings()


class InMemoryRedis:
    """Minimal Redis-like interface for local testing."""

    def __init__(self) -> None:
        """Initialize in-memory store."""
        self._store: Dict[str, object] = {}

    def set(self, key: str, value: object) -> None:
        """Set a key."""
        self._store[key] = value

    def get(self, key: str):
        """Get a key value."""
        return self._store.get(key)

    def lrange(self, key: str, start: int, end: int):
        """Return a slice from a list."""
        data = self._store.get(key, [])
        return data[start : end + 1]

    def hset(self, key: str, mapping: dict) -> None:
        """Set hash mapping."""
        self._store[key] = mapping


logger = configure_logger("storeiq-api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Configure application resources."""
    # Database tables
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        logger.warning("Failed to create database tables: %s", exc)

    # Load POS transactions from reference dataset if available
    try:
        from pathlib import Path
        from pipeline.pos_loader import load_pos_transactions

        pos_candidates = [
            Path("/app/dataset/Brigade_Bangalore_10_April_26 (1)bc6219c.csv"),
            Path(__file__).resolve().parent.parent
            / "dataset"
            / "Brigade_Bangalore_10_April_26 (1)bc6219c.csv",
        ]
        for pos_path in pos_candidates:
            if pos_path.exists():
                count = load_pos_transactions(str(pos_path), settings.database_url)
                logger.info("Loaded %s POS transactions from %s", count, pos_path)
                break
    except Exception as exc:
        logger.warning("POS transaction load skipped: %s", exc)

    # Seed baseline metrics only (for peak hours / anomaly baselines)
    try:
        from sqlalchemy.orm import Session
        from database.models import MetricsHourly
        from database.seed import seed_metrics_only

        with Session(engine) as db:
            if db.query(MetricsHourly).count() == 0:
                seed_metrics_only()
                logger.info("Seeded baseline hourly metrics")
    except Exception as exc:
        logger.warning("Metrics seed skipped: %s", exc)

    # Redis connection with fallback
    try:
        client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
        client.ping()
        app.state.redis = client
        logger.info("Redis connected at %s", settings.redis_url)
    except Exception as exc:
        logger.warning("Redis unavailable, using in-memory fallback: %s", exc)
        app.state.redis = InMemoryRedis()

    # Singleton Kafka producer
    try:
        producer = KafkaProducerClient(settings.kafka_bootstrap)
        await producer.start()
        app.state.kafka_producer = producer
        logger.info("Kafka producer connected at %s", settings.kafka_bootstrap)
    except Exception as exc:
        logger.warning("Kafka producer failed to start: %s", exc)
        app.state.kafka_producer = None

    app.state.logger = logger
    app.state.websocket_manager = ConnectionManager()
    app.state.started_at = time.time()
    app.state.broadcast_task = asyncio.create_task(
        periodic_broadcast(app.state.websocket_manager, lambda: metrics.get_live_payload(app.state))
    )

    # Kafka consumer — persist pipeline events to PostgreSQL
    try:
        from api.kafka_service import EventIngestConsumer

        consumer = EventIngestConsumer()
        await consumer.start()
        app.state.kafka_consumer = consumer
        logger.info("Kafka event ingest consumer started")
    except Exception as exc:
        logger.warning("Kafka consumer failed to start: %s", exc)
        app.state.kafka_consumer = None

    yield

    # Cleanup
    app.state.broadcast_task.cancel()
    if getattr(app.state, "kafka_consumer", None):
        try:
            await app.state.kafka_consumer.stop()
        except Exception as exc:
            logger.warning("Kafka consumer shutdown error: %s", exc)
    if app.state.kafka_producer:
        try:
            await app.state.kafka_producer.stop()
        except Exception as exc:
            logger.warning("Kafka producer shutdown error: %s", exc)


app = FastAPI(title="Purplle StoreIQ", lifespan=lifespan, version="1.0.0")
app.state.logger = logger

# Rate limiter
app.state.limiter = limiter


def rate_limit_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    """Return a 429 response when rate limit is exceeded."""
    return JSONResponse(
        status_code=429,
        content={"detail": "Rate limit exceeded. Try again later."},
    )


app.add_exception_handler(RateLimitExceeded, rate_limit_handler)
app.add_middleware(SlowAPIMiddleware)

def db_error_handler(request: Request, exc: OperationalError) -> JSONResponse:
    """Return a 503 response during database outages."""
    return JSONResponse(
        status_code=503,
        content={"detail": "Database temporarily unavailable. Please retry."},
    )


app.add_exception_handler(OperationalError, db_error_handler)

# CORS — restricted to configured origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    allow_credentials=True,
)


# API Key authentication middleware
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """Validate API key for non-public endpoints."""
    # Skip auth for health, docs, openapi, and prometheus endpoints
    skip_paths = {"/health", "/docs", "/openapi.json", "/redoc", "/metrics/prometheus"}
    if request.url.path in skip_paths or not settings.api_key:
        return await call_next(request)

    api_key = request.headers.get("X-API-Key", "")
    if api_key != settings.api_key:
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid or missing API key"},
        )
    return await call_next(request)


# Structured logging middleware
app.middleware("http")(logging_middleware)

# Routers
app.include_router(events.router)
app.include_router(metrics.router)
app.include_router(funnel.router)
app.include_router(heatmap.router)
app.include_router(anomalies.router)
app.include_router(predict.router)
app.include_router(health.router)


@app.get("/metrics/prometheus")
async def prometheus_metrics():
    """Expose Prometheus metrics."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.websocket("/ws/live")
async def websocket_live(websocket: WebSocket):
    """WebSocket endpoint for live dashboard updates."""
    manager: ConnectionManager = app.state.websocket_manager
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        manager.disconnect(websocket)
