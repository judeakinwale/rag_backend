from unittest.mock import AsyncMock

import pytest

from app.events.user_events import UserCreatedEvent, UserDeletedEvent, UserUpdatedEvent
from app.producers.user_producer import UserProducer


@pytest.mark.asyncio
async def test_test_event_publishes_to_test_topic():
    kafka_producer = AsyncMock()
    producer = UserProducer(kafka_producer)

    await producer.test({"hello": "world"}, key="abc")

    kafka_producer.publish.assert_awaited_once_with(
        "test.topic", {"hello": "world"}, "abc"
    )


@pytest.mark.asyncio
async def test_user_created_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = UserProducer(kafka_producer)
    event = UserCreatedEvent(id=1, email="user@example.com", name="User")

    await producer.user_created(event)

    kafka_producer.publish.assert_awaited_once_with(
        "user.created",
        event.model_dump(),
        None,
    )


@pytest.mark.asyncio
async def test_user_updated_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = UserProducer(kafka_producer)
    event = UserUpdatedEvent(
        id=1,
        email="user@example.com",
        name="User",
        updated=["name"],
    )

    await producer.user_updated(event, key="user-1")

    kafka_producer.publish.assert_awaited_once_with(
        "user.updated",
        event.model_dump(),
        "user-1",
    )


@pytest.mark.asyncio
async def test_user_deleted_publishes_serialized_event():
    kafka_producer = AsyncMock()
    producer = UserProducer(kafka_producer)
    event = UserDeletedEvent(id=1, email="user@example.com", name="User")

    await producer.user_deleted(event)

    kafka_producer.publish.assert_awaited_once_with(
        "user.deleted",
        event.model_dump(),
        None,
    )