"""Unit tests for the Kafka producer and consumer wrappers."""
# PROMPT: Write unit tests for KafkaProducerClient and KafkaConsumerClient using mocks.
# CHANGES MADE: Added async send/stop tests with mocked aiokafka producer; no real broker required.

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from streaming.kafka_producer import KafkaProducerClient


@pytest.mark.asyncio
async def test_producer_send_without_start():
    """Sending without starting should be a no-op."""
    producer = KafkaProducerClient("localhost:9092")
    # Should not raise
    await producer.send("test-topic", {"key": "value"})


@pytest.mark.asyncio
async def test_producer_stop_without_start():
    """Stopping without starting should be safe."""
    producer = KafkaProducerClient("localhost:9092")
    await producer.stop()  # Should not raise


@pytest.mark.asyncio
async def test_producer_lifecycle():
    """Producer should handle start/send/stop lifecycle."""
    with patch("streaming.kafka_producer.AIOKafkaProducer") as MockProducer:
        mock_instance = AsyncMock()
        MockProducer.return_value = mock_instance

        producer = KafkaProducerClient("localhost:9092")
        await producer.start()
        MockProducer.assert_called_once_with(
        bootstrap_servers="localhost:9092",
        acks="all",
        retry_backoff_ms=100,
        request_timeout_ms=10000,
    )
        mock_instance.start.assert_called_once()

        await producer.send("test-topic", {"key": "value"})
        mock_instance.send_and_wait.assert_called_once()

        await producer.stop()
        mock_instance.stop.assert_called_once()
