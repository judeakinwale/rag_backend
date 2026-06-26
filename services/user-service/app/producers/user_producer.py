from rag_packages.shared.kafka.producer import KafkaProducer
from app.events.user_events import (
    UserCreatedEvent,
    UserUpdatedEvent,
    UserSoftDeletedEvent,
    UserDeletedEvent,
)


class UserProducer:
    def __init__(self, producer: KafkaProducer):
        self.producer = producer

    async def test(self, event: dict, key: str | None = None):
        await self.producer.publish(
            "test.topic",
            event,
            key,
        )

    async def user_created(self, event: UserCreatedEvent, key: str | None = None):
        await self.producer.publish(
            "user.created",
            event.model_dump(),
            key,
        )

    async def user_updated(self, event: UserUpdatedEvent, key: str | None = None):
        await self.producer.publish(
            "user.updated",
            event.model_dump(),
            key,
        )

    async def user_softdeleted(
        self, event: UserSoftDeletedEvent, key: str | None = None
    ):
        await self.producer.publish(
            "user.softdeleted",
            event.model_dump(),
            key,
        )

    async def user_deleted(self, event: UserDeletedEvent, key: str | None = None):
        await self.producer.publish(
            "user.deleted",
            event.model_dump(),
            key,
        )
