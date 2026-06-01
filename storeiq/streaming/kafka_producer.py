"""Kafka producer utilities."""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

import orjson
from aiokafka import AIOKafkaProducer

logger = logging.getLogger("storeiq-api")


class KafkaProducerClient:
    """Async Kafka producer wrapper with orjson serialization."""

    def __init__(self, bootstrap_servers: str) -> None:
        """Initialize producer configuration."""
        self._bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self) -> None:
        """Start the Kafka producer."""
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self._bootstrap_servers,
            acks="all",
            retry_backoff_ms=100,
            request_timeout_ms=10000,
        )
        await self._producer.start()
        logger.info("Kafka producer started: %s", self._bootstrap_servers)

    async def stop(self) -> None:
        """Stop the Kafka producer."""
        if self._producer:
            await self._producer.stop()
            logger.info("Kafka producer stopped")

    async def send(self, topic: str, payload: Dict[str, Any]) -> None:
        """Send a JSON message to a topic using orjson for fast serialization."""
        if not self._producer:
            return
        await self._producer.send_and_wait(topic, orjson.dumps(payload, default=str))
