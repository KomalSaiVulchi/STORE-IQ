"""Kafka consumer service — persists events and evaluates anomalies."""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from api.config import get_settings
from api.db import SessionLocal
from api.event_processor import evaluate_live_anomalies, persist_event
from streaming.kafka_consumer import KafkaConsumerWorker

logger = logging.getLogger("storeiq-api")


class EventIngestConsumer:
    """Background consumer that writes Kafka events to PostgreSQL."""

    def __init__(self) -> None:
        settings = get_settings()
        self._worker = KafkaConsumerWorker(
            bootstrap_servers=settings.kafka_bootstrap,
            topic=settings.kafka_raw_topic,
            group_id="storeiq-api-ingest",
        )
        self._worker.register_handler(self._handle_message)
        self._task: Optional[asyncio.Task] = None
        self._anomaly_task: Optional[asyncio.Task] = None
        self._event_count = 0

    def _handle_message(self, payload: dict) -> None:
        """Persist a single Kafka event payload."""
        db = SessionLocal()
        try:
            persist_event(db, payload)
            self._event_count += 1
            if self._event_count % 50 == 0:
                evaluate_live_anomalies(db)
        except Exception as exc:
            logger.warning("Failed to persist Kafka event: %s", exc)
            db.rollback()
        finally:
            db.close()

    async def start(self) -> None:
        """Start Kafka consumer and periodic anomaly evaluation."""
        self._task = asyncio.create_task(self._worker.start())
        self._anomaly_task = asyncio.create_task(self._anomaly_loop())
        logger.info("Event ingest consumer started")

    async def stop(self) -> None:
        """Stop background tasks."""
        if self._anomaly_task:
            self._anomaly_task.cancel()
        if self._task:
            self._task.cancel()
        try:
            await self._worker.stop()
        except Exception as exc:
            logger.warning("Consumer stop error: %s", exc)

    async def _anomaly_loop(self, interval: float = 60.0) -> None:
        """Periodically evaluate live anomalies."""
        while True:
            await asyncio.sleep(interval)
            db = SessionLocal()
            try:
                evaluate_live_anomalies(db)
            except Exception as exc:
                logger.warning("Anomaly evaluation failed: %s", exc)
            finally:
                db.close()
