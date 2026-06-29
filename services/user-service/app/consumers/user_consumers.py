from app.events import user_events
from rag_packages.contracts.events import shared_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.core.config import settings
from app.core.redis import generate_cache_key, r


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_test_event(event: dict):
    print(f"[{service_name}] Handling test.topic event: {event}")


async def handle_user_created(event: user_events.UserCreatedEvent):
    print(f"[{service_name}] Handling user.created event: {event}")


async def handle_user_updated(event: user_events.UserUpdatedEvent):
    print(f"[{service_name}] Handling user.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_user_softdeleted(event: user_events.UserSoftDeletedEvent):
    print(f"[{service_name}] Handling user.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_user_deleted(event: user_events.UserDeletedEvent):
    print(f"[{service_name}] Handling user.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_user_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling user.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_created(original_event) if valid else None


async def handle_user_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling user.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_updated(original_event) if valid else None


async def handle_user_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling user.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_softdeleted(original_event) if valid else None


async def handle_user_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling user.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_deleted(original_event) if valid else None
