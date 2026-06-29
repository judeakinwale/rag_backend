from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.ingest_events import (
    IngestCompletedEvent,
    IngestStartedEvent,
    ProcessingStartedEvent,
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

    async def ingest_started(self, event: IngestStartedEvent, key: str | None = None):
        await self.producer.publish(
            "ingest.started",
            event.model_dump(),
            key,
        )

    async def processing_started(
        self, event: ProcessingStartedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.processing",
            event.model_dump(),
            key,
        )

    async def ingest_completed(
        self, event: IngestCompletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "ingest.completed",
            event.model_dump(),
            key,
        )
