from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.document_events import (
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentSoftDeletedEvent,
    DocumentDeletedEvent,
)


class DocumentProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    # document processed and stored in vector db before storing in db
    async def document_processed(
        self, event: DocumentCreatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "document.processed",
            event.model_dump(),
            key,
        )

    async def document_created(
        self, event: DocumentCreatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "document.created",
            event.model_dump(),
            key,
        )

    async def document_updated(
        self, event: DocumentUpdatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "document.updated",
            event.model_dump(),
            key,
        )

    async def document_softdeleted(
        self, event: DocumentSoftDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "document.softdeleted",
            event.model_dump(),
            key,
        )

    async def document_deleted(
        self, event: DocumentDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "document.deleted",
            event.model_dump(),
            key,
        )
