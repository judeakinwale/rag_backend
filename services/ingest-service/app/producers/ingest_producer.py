from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.ingest_events import (
    IngestCreatedEvent,
    IngestUpdatedEvent,
    IngestSoftDeletedEvent,
    IngestDeletedEvent,
)


class IngestProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def test(self, event: dict, key: str | None = None):
        await self.producer.publish(
            "test.topic",
            event,
            key,
        )

    async def ingest_created(self, event: IngestCreatedEvent, key: str | None = None):
        await self.producer.publish(
            "ingest.created",
            event.model_dump(),
            key,
        )

    async def ingest_updated(self, event: IngestUpdatedEvent, key: str | None = None):
        await self.producer.publish(
            "ingest.updated",
            event.model_dump(),
            key,
        )

    async def ingest_softdeleted(
        self, event: IngestSoftDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.softdeleted",
            event.model_dump(),
            key,
        )

    async def ingest_deleted(self, event: IngestDeletedEvent, key: str | None = None):
        await self.producer.publish(
            "ingest.deleted",
            event.model_dump(),
            key,
        )
