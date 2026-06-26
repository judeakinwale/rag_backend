from unittest.mock import AsyncMock

import pytest

from app.events.ingest_events import IngestCreatedEvent, IngestDeletedEvent, IngestUpdatedEvent
from app.producers.ingest_producer import IngestProducer


@pytest.mark.asyncio
async def test_test_event_publishes_to_test_topic():
    kafka_producer = AsyncMock()
    producer = IngestProducer(kafka_producer)

    await producer.test({"hello": "world"}, key="abc")

    kafka_producer.publish.assert_awaited_once_with(
        "test.topic", {"hello": "world"}, "abc"
    )


@pytest.mark.asyncio
async def test_ingest_created_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = IngestProducer(kafka_producer)
    event = IngestCreatedEvent(id=1, email="ingest@example.com", name="Ingest")

    await producer.ingest_created(event)

    kafka_producer.publish.assert_awaited_once_with(
        "ingest.created",
        event.model_dump(),
        None,
    )


@pytest.mark.asyncio
async def test_ingest_updated_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = IngestProducer(kafka_producer)
    event = IngestUpdatedEvent(
        id=1,
        email="ingest@example.com",
        name="Ingest",
        updated=["name"],
    )

    await producer.ingest_updated(event, key="ingest-1")

    kafka_producer.publish.assert_awaited_once_with(
        "ingest.updated",
        event.model_dump(),
        "ingest-1",
    )


@pytest.mark.asyncio
async def test_ingest_deleted_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = IngestProducer(kafka_producer)
    event = IngestDeletedEvent(id=1, email="ingest@example.com", name="Ingest")

    await producer.ingest_deleted(event)

    kafka_producer.publish.assert_awaited_once_with(
        "ingest.deleted",
        event.model_dump(),
        None,
    )