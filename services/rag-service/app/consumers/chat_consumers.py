from rag_packages.contracts.events import shared_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.events import chat_events
from app.core.config import settings
from app.core.redis import generate_cache_key, r


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_chat_created(event: chat_events.ChatCreatedEvent):
    print(f"[{service_name}] Handling chat.created event: {event}")


async def handle_chat_updated(event: chat_events.ChatUpdatedEvent):
    print(f"[{service_name}] Handling chat.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_chat_softdeleted(event: chat_events.ChatSoftDeletedEvent):
    print(f"[{service_name}] Handling chat.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_chat_deleted(event: chat_events.ChatDeletedEvent):
    print(f"[{service_name}] Handling chat.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_chat_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling chat.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_chat_created(original_event) if valid else None


async def handle_chat_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling chat.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_chat_updated(original_event) if valid else None


async def handle_chat_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling chat.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_chat_softdeleted(original_event) if valid else None


async def handle_chat_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling chat.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_chat_deleted(original_event) if valid else None
