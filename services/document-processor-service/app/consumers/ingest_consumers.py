from rag_packages.contracts.events import shared_events, ingest as ingest_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.core.config import settings
from app.events.events import EVENTS
from app.consumers.ingest_consumer_utils import IngestConsumerUtils


service_name = settings.APP_NAME
consumer_utils = IngestConsumerUtils()
validate_original_event = KafkaConsumer.validate_dlq_original_event

# Force container build


async def handle_ingest_started(event: ingest_events.IngestStartedEvent):
    print(f"[{service_name}] Handling ingest.started event: {event}")


async def handle_processing_started(event: ingest_events.ProcessingStartedEvent):
    print(f"[{service_name}] Handling ingest.processing event: {event}")

    try:
        await consumer_utils.process_event_document(event)
    except Exception as e:
        print(f"[{service_name}] Error processing document [ingest.processing]: {e}")
        await consumer_utils.trigger_processing_failed(event, error=e)

    print(f"[{service_name}] Handling ingest.processing event done: {event}")


async def handle_processing_completed(event: ingest_events.ProcessingCompletedEvent):
    print(f"[{service_name}] Handling ingest.processing.completed event: {event}")

    try:
        await consumer_utils.event_document_processed(event)
    except Exception as e:
        print(f"[{service_name}] Error processing document [ingest.processing.completed]: {e}")
        await consumer_utils.trigger_processing_failed(event, error=e)

    print(f"[{service_name}] Handling ingest.processing.completed event done: {event}")


async def handle_processing_failed(event: ingest_events.ProcessingFailedEvent):
    print(f"[{service_name}] Handling ingest.processing.failed event: {event}")


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


async def handle_processing_completed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.processing.completed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_processing_completed(original_event) if valid else None


async def handle_processing_failed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.processing.failed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_processing_failed(original_event) if valid else None


async def handle_ingest_completed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling ingest.completed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_ingest_completed(original_event) if valid else None
