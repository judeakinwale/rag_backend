from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from rag_packages.contracts.events.document import (
    DocumentCreatedEvent,
    DocumentDeletedEvent,
    DocumentUpdatedEvent,
)
from app.producers.document_producer import DocumentProducer


TIMESTAMP = datetime(2024, 1, 1, tzinfo=UTC)


@pytest.mark.asyncio
async def test_document_created_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = DocumentProducer(kafka_producer)
    event = DocumentCreatedEvent(
        id=1,
        name="Document",
        file_url="https://contoso.example/docs/1.pdf",
        source="sharepoint",
        ingest_initiated_at=TIMESTAMP,
    )

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
        name="Document",
        file_url="https://contoso.example/docs/1.pdf",
        source="sharepoint",
        ingest_initiated_at=TIMESTAMP,
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
    event = DocumentDeletedEvent(
        id=1,
        name="Document",
        file_url="https://contoso.example/docs/1.pdf",
        source="sharepoint",
        ingest_initiated_at=TIMESTAMP,
    )

    await producer.document_deleted(event)

    kafka_producer.publish.assert_awaited_once_with(
        "document.deleted",
        event.model_dump(),
        None,
    )
