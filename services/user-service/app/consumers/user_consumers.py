from typing import TypeVar
from app.events import user_events
from rag_packages.contracts.events import shared_events
from app.events.events import EVENTS
from app.core.redis import generate_cache_key, r

T = TypeVar("T", bound=shared_events.BaseEvent)


def validate_dlq_original_event(
    event: shared_events.DLQEvent, events_dict: dict[str, T]
) -> tuple[T, bool]:
    original_event_model = events_dict.get(event.original_topic)
    original_event = event.payload

    try:
        if not original_event_model:
            return original_event, False

        valid_event = original_event_model.model_validate(original_event)
        return valid_event, True

    except Exception as e:
        print(f"[user-service] Failed to validate event: {event}. Error: {e}")
        return original_event, False


async def handle_test_event(event: dict):
    print(f"[user-service] Handling test.topic event: {event}")


async def handle_user_created(event: user_events.UserCreatedEvent):
    print(f"[user-service] Handling user.created event: {event}")


async def handle_user_updated(event: user_events.UserUpdatedEvent):
    print(f"[user-service] Handling user.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_user_softdeleted(event: user_events.UserSoftDeletedEvent):
    print(f"[user-service] Handling user.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_user_deleted(event: user_events.UserDeletedEvent):
    print(f"[user-service] Handling user.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)

# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq

async def handle_user_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[user-service] Handling user.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_created(original_event) if valid else None


async def handle_user_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[user-service] Handling user.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_updated(original_event) if valid else None


async def handle_user_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[user-service] Handling user.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_softdeleted(original_event) if valid else None


async def handle_user_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[user-service] Handling user.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_user_deleted(original_event) if valid else None
