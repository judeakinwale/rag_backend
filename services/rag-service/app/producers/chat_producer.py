from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.chat_events import (
    ChatCreatedEvent,
    ChatUpdatedEvent,
    ChatSoftDeletedEvent,
    ChatDeletedEvent,
)


class ChatProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def chat_created(self, event: ChatCreatedEvent, key: str | None = None):
        await self.producer.publish(
            "chat.created",
            event.model_dump(),
            key,
        )

    async def chat_updated(self, event: ChatUpdatedEvent, key: str | None = None):
        await self.producer.publish(
            "chat.updated",
            event.model_dump(),
            key,
        )

    async def chat_softdeleted(
        self, event: ChatSoftDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "chat.softdeleted",
            event.model_dump(),
            key,
        )

    async def chat_deleted(self, event: ChatDeletedEvent, key: str | None = None):
        await self.producer.publish(
            "chat.deleted",
            event.model_dump(),
            key,
        )
