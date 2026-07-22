from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.contracts.events.document import (
    DocumentCreatedEvent,
    DocumentProcessedEvent,
    DocumentUpdatedEvent,
    DocumentSoftDeletedEvent,
    DocumentDeletedEvent,
)
from rag_packages.shared.utils.format import get_date_iso_str


class DocumentProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    # document processed and stored in vector db before storing in db
    async def document_processed(
        self, event: DocumentProcessedEvent, key: str | None = None
    ):
        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "document.processed",
            data,
            key,
        )

    async def document_created(
        self, event: DocumentCreatedEvent, key: str | None = None
    ):
        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "document.created",
            data,
            key,
        )

    async def document_updated(
        self, event: DocumentUpdatedEvent, key: str | None = None
    ):
        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "document.updated",
            data,
            key,
        )

    async def document_softdeleted(
        self, event: DocumentSoftDeletedEvent, key: str | None = None
    ):
        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "document.softdeleted",
            data,
            key,
        )

    async def document_deleted(
        self, event: DocumentDeletedEvent, key: str | None = None
    ):
        data = event.model_dump()
        data["ingest_initiated_at"] = get_date_iso_str(event.ingest_initiated_at)

        await self.producer.publish(
            "document.deleted",
            data,
            key,
        )
