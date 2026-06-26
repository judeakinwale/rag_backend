from typing import TypeVar
from app.events import ingest_events
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
        print(f"[ingest-service] Failed to validate event: {event}. Error: {e}")
        return original_event, False


async def handle_test_event(event: dict):
    print(f"[ingest-service] Handling test.topic event: {event}")


async def handle_ingest_created(event: ingest_events.IngestCreatedEvent):
    print(f"[ingest-service] Handling ingest.created event: {event}")


async def handle_ingest_updated(event: ingest_events.IngestUpdatedEvent):
    print(f"[ingest-service] Handling ingest.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_ingest_softdeleted(event: ingest_events.IngestSoftDeletedEvent):
    print(f"[ingest-service] Handling ingest.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_ingest_deleted(event: ingest_events.IngestDeletedEvent):
    print(f"[ingest-service] Handling ingest.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)

# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq

async def handle_ingest_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[ingest-service] Handling ingest.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_created(original_event) if valid else None


async def handle_ingest_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[ingest-service] Handling ingest.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_updated(original_event) if valid else None


async def handle_ingest_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[ingest-service] Handling ingest.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_softdeleted(original_event) if valid else None


async def handle_ingest_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_dlq_original_event(event, EVENTS)
    print(
        f"[ingest-service] Handling ingest.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_deleted(original_event) if valid else None
