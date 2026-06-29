from app.events import ingest_events
from rag_packages.contracts.events import shared_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.core.config import settings


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_ingest_started(event: ingest_events.IngestStartedEvent):
    print(f"[{service_name}] Handling ingest.started event: {event}")


async def handle_processing_started(event: ingest_events.ProcessingStartedEvent):
    print(f"[{service_name}] Handling ingest.processing event: {event}")


async def handle_ingest_completed(event: ingest_events.IngestCompletedEvent):
    print(f"[{service_name}] Handling ingest.completed event: {event}")


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_ingest_started_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.started.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_started(original_event) if valid else None


async def handle_processing_started_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.processing.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_processing_started(original_event) if valid else None


async def handle_ingest_completed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.completed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_completed(original_event) if valid else None
