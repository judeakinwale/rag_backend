from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.vector_document_events import (
    VectorDocumentCreatedEvent,
    VectorDocumentUpdatedEvent,
    VectorDocumentSoftDeletedEvent,
    VectorDocumentDeletedEvent,
)
from rag_packages.shared.utils.format import get_date_iso_str


class VectorDocumentProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    # document processed and stored in vector db before storing in db
    async def document_processed(
        self, event: VectorDocumentCreatedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["initiated_at"] = get_date_iso_str(event.initiated_at)

        await self.producer.publish(
            "vector_document.processed",
            data,
            key,
        )

    async def document_created(
        self, event: VectorDocumentCreatedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["initiated_at"] = get_date_iso_str(event.initiated_at)

        await self.producer.publish(
            "vector_document.created",
            data,
            key,
        )

    async def document_updated(
        self, event: VectorDocumentUpdatedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["initiated_at"] = get_date_iso_str(event.initiated_at)

        await self.producer.publish(
            "vector_document.updated",
            data,
            key,
        )

    async def document_softdeleted(
        self, event: VectorDocumentSoftDeletedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["initiated_at"] = get_date_iso_str(event.initiated_at)

        await self.producer.publish(
            "vector_document.softdeleted",
            data,
            key,
        )

    async def document_deleted(
        self, event: VectorDocumentDeletedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["initiated_at"] = get_date_iso_str(event.initiated_at)

        await self.producer.publish(
            "vector_document.deleted",
            data,
            key,
        )
