from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.vector_document_events import (
    VectorDocumentCreatedEvent,
    VectorDocumentUpdatedEvent,
    VectorDocumentSoftDeletedEvent,
    VectorDocumentDeletedEvent,
)


class VectorDocumentProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    # document processed and stored in vector db before storing in db
    async def document_processed(
        self, event: VectorDocumentCreatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "vector_document.processed",
            event.model_dump(),
            key,
        )

    async def document_created(
        self, event: VectorDocumentCreatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "vector_document.created",
            event.model_dump(),
            key,
        )

    async def document_updated(
        self, event: VectorDocumentUpdatedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "vector_document.updated",
            event.model_dump(),
            key,
        )

    async def document_softdeleted(
        self, event: VectorDocumentSoftDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "vector_document.softdeleted",
            event.model_dump(),
            key,
        )

    async def document_deleted(
        self, event: VectorDocumentDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "vector_document.deleted",
            event.model_dump(),
            key,
        )
