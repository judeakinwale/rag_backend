from rag_packages.contracts.events import shared_events, document as document_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.core.config import settings
from app.core.redis import generate_cache_key, r


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_document_created(event: document_events.DocumentCreatedEvent):
    print(f"[{service_name}] Handling document.created event: {event}")


async def handle_document_processed(event: document_events.DocumentProcessedEvent):
    print(f"[{service_name}] Handling document.processed event: {event}")


async def handle_document_updated(event: document_events.DocumentUpdatedEvent):
    print(f"[{service_name}] Handling document.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_document_softdeleted(event: document_events.DocumentSoftDeletedEvent):
    print(f"[{service_name}] Handling document.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_document_deleted(event: document_events.DocumentDeletedEvent):
    print(f"[{service_name}] Handling document.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_document_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling document.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_document_created(original_event) if valid else None


async def handle_document_processed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling document.processed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_document_processed(original_event) if valid else None


async def handle_document_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling document.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_document_updated(original_event) if valid else None


async def handle_document_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling document.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_document_softdeleted(original_event) if valid else None


async def handle_document_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling document.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_document_deleted(original_event) if valid else None
