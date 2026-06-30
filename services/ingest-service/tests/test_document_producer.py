from unittest.mock import AsyncMock

import pytest

from app.events.document_events import DocumentStartedEvent, DocumentDeletedEvent, DocumentUpdatedEvent
from app.producers.document_producer import DocumentProducer


@pytest.mark.asyncio
async def test_test_event_publishes_to_test_topic():
    kafka_producer = AsyncMock()
    producer = DocumentProducer(kafka_producer)

    await producer.test({"hello": "world"}, key="abc")

    kafka_producer.publish.assert_awaited_once_with(
        "test.topic", {"hello": "world"}, "abc"
    )


@pytest.mark.asyncio
async def test_document_created_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = DocumentProducer(kafka_producer)
    event = DocumentStartedEvent(id=1, email="document@example.com", name="Document")

    await producer.document_created(event)

    kafka_producer.publish.assert_awaited_once_with(
        "document.created",
        event.model_dump(),
        None,
    )


@pytest.mark.asyncio
async def test_document_updated_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = DocumentProducer(kafka_producer)
    event = DocumentUpdatedEvent(
        id=1,
        email="document@example.com",
        name="Document",
        updated=["name"],
    )

    await producer.document_updated(event, key="document-1")

    kafka_producer.publish.assert_awaited_once_with(
        "document.updated",
        event.model_dump(),
        "document-1",
    )


@pytest.mark.asyncio
async def test_document_deleted_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = DocumentProducer(kafka_producer)
    event = DocumentDeletedEvent(id=1, email="document@example.com", name="Document")

    await producer.document_deleted(event)

    kafka_producer.publish.assert_awaited_once_with(
        "document.deleted",
        event.model_dump(),
        None,
    )