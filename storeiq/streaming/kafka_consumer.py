"""Kafka consumer workers for analytics and anomalies."""

from __future__ import annotations

import logging
from typing import Callable, Dict, Optional

import orjson
from aiokafka import AIOKafkaConsumer

logger = logging.getLogger("storeiq-api")


class KafkaConsumerWorker:
    """Async Kafka consumer wrapper with error handling."""

    def __init__(self, bootstrap_servers: str, topic: str, group_id: str) -> None:
        """Configure consumer parameters."""
        self._consumer = AIOKafkaConsumer(
            topic,
            bootstrap_servers=bootstrap_servers,
            group_id=group_id,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            auto_commit_interval_ms=5000,
        )
        self._handler: Optional[Callable[[Dict[str, object]], None]] = None
        self._topic = topic

    def register_handler(self, handler: Callable[[Dict[str, object]], None]) -> None:
        """Register a message handler callback."""
        self._handler = handler

    async def start(self) -> None:
        """Start the consumer loop with error handling."""
        await self._consumer.start()
        logger.info("Kafka consumer started for topic: %s", self._topic)
        try:
            async for message in self._consumer:
                if not self._handler:
                    continue
                try:
                    payload = orjson.loads(message.value)
                    self._handler(payload)
                except orjson.JSONDecodeError as exc:
                    logger.warning(
                        "Failed to decode message on topic %s: %s",
                        self._topic,
                        exc,
                    )
                except Exception as exc:
                    logger.error(
                        "Handler error on topic %s: %s",
                        self._topic,
                        exc,
                    )
        except Exception as exc:
            logger.error("Consumer loop error on topic %s: %s", self._topic, exc)
            raise

    async def stop(self) -> None:
        """Stop the consumer."""
        await self._consumer.stop()
        logger.info("Kafka consumer stopped for topic: %s", self._topic)
