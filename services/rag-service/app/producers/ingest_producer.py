from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.rag_events import (
    RagCompletedEvent,
    RagStartedEvent,
    ProcessingStartedEvent,
)


class RagProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def test(self, event: dict, key: str | None = None):
        await self.producer.publish(
            "test.topic",
            event,
            key,
        )

    async def rag_started(self, event: RagStartedEvent, key: str | None = None):
        await self.producer.publish(
            "rag.started",
            event.model_dump(),
            key,
        )

    async def processing_started(
        self, event: ProcessingStartedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "rag.processing",
            event.model_dump(),
            key,
        )

    async def rag_completed(
        self, event: RagCompletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "rag.completed",
            event.model_dump(),
            key,
        )
