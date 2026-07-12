from app.events import vector_document_events
from rag_packages.contracts.events import shared_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.core.config import settings
from app.core.redis import generate_cache_key, r


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_vector_document_created(event: vector_document_events.VectorDocumentCreatedEvent):
    print(f"[{service_name}] Handling vector_document.created event: {event}")


async def handle_vector_document_processed(event: vector_document_events.VectorDocumentProcessedEvent):
    print(f"[{service_name}] Handling vector_document.processed event: {event}")


async def handle_vector_document_updated(event: vector_document_events.VectorDocumentUpdatedEvent):
    print(f"[{service_name}] Handling vector_document.updated event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)  # invalidate cache


async def handle_vector_document_softdeleted(event: vector_document_events.VectorDocumentSoftDeletedEvent):
    print(f"[{service_name}] Handling vector_document.softdeleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


async def handle_vector_document_deleted(event: vector_document_events.VectorDocumentDeletedEvent):
    print(f"[{service_name}] Handling vector_document.deleted event: {event}")
    cache_key = generate_cache_key(str(event.id))
    await r.delete(cache_key)


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_vector_document_created_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling vector_document.created.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_vector_document_created(original_event) if valid else None


async def handle_vector_document_processed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling vector_document.processed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_vector_document_processed(original_event) if valid else None


async def handle_vector_document_updated_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling vector_document.updated.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_vector_document_updated(original_event) if valid else None


async def handle_vector_document_softdeleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling vector_document.softdeleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_vector_document_softdeleted(original_event) if valid else None


async def handle_vector_document_deleted_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling vector_document.deleted.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_vector_document_deleted(original_event) if valid else None
