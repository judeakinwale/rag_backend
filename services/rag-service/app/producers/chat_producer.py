from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.chat_events import (
    ChatCreatedEvent,
    ChatUpdatedEvent,
    ChatSoftDeletedEvent,
    ChatDeletedEvent,
)
from rag_packages.shared.utils.format import get_date_iso_str


class ChatProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def chat_created(self, event: ChatCreatedEvent, key: str | None = None):

        data = event.model_dump()
        data["created_at"] = get_date_iso_str(event.created_at)

        await self.producer.publish(
            "chat.created",
            data,
            key,
        )

    async def chat_updated(self, event: ChatUpdatedEvent, key: str | None = None):

        data = event.model_dump()
        data["created_at"] = get_date_iso_str(event.created_at)

        await self.producer.publish(
            "chat.updated",
            data,
            key,
        )

    async def chat_softdeleted(
        self, event: ChatSoftDeletedEvent, key: str | None = None
    ):

        data = event.model_dump()
        data["created_at"] = get_date_iso_str(event.created_at)

        await self.producer.publish(
            "chat.softdeleted",
            data,
            key,
        )

    async def chat_deleted(self, event: ChatDeletedEvent, key: str | None = None):

        data = event.model_dump()
        data["created_at"] = get_date_iso_str(event.created_at)

        await self.producer.publish(
            "chat.deleted",
            data,
            key,
        )
