from app.events import rag_events
from rag_packages.contracts.events import shared_events
from rag_packages.shared.kafka.consumer import KafkaConsumer
from app.events.events import EVENTS
from app.core.config import settings


service_name = settings.APP_NAME
validate_original_event = KafkaConsumer.validate_dlq_original_event


async def handle_rag_started(event: rag_events.RagStartedEvent):
    print(f"[{service_name}] Handling rag.started event: {event}")


async def handle_processing_started(event: rag_events.ProcessingStartedEvent):
    print(f"[{service_name}] Handling rag.processing event: {event}")


async def handle_rag_completed(event: rag_events.RagCompletedEvent):
    print(f"[{service_name}] Handling rag.completed event: {event}")


# TODO: implement DLQ handler with replay and send to parking lot topic for failed dlq


async def handle_rag_started_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling rag.started.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_rag_started(original_event) if valid else None


async def handle_processing_started_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling rag.processing.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_processing_started(original_event) if valid else None


async def handle_rag_completed_dlq(event: shared_events.DLQEvent):
    original_event, valid = validate_original_event(event, EVENTS)
    print(
        f"[{service_name}] Handling rag.completed.dlq event: {event}, original_event: {original_event}"
    )
    # await handle_rag_completed(original_event) if valid else None
