from app.events import ingest_events, document_events
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "ingest.started": ingest_events.IngestStartedEvent,
    "ingest.started.dlq": DLQEvent,
    "ingest.processing": ingest_events.ProcessingStartedEvent,
    "ingest.processing.dlq": DLQEvent,
    "ingest.completed": ingest_events.IngestCompletedEvent,
    "ingest.completed.dlq": DLQEvent,
    # ________________________________________________________________
    "document.created": document_events.DocumentCreatedEvent,
    "document.created.dlq": DLQEvent,
    "document.processed": document_events.DocumentProcessedEvent,
    "document.processed.dlq": DLQEvent,
    "document.updated": document_events.DocumentUpdatedEvent,
    "document.updated.dlq": DLQEvent,
    "document.softdeleted": document_events.DocumentSoftDeletedEvent,
    "document.softdeleted.dlq": DLQEvent,
    "document.deleted": document_events.DocumentDeletedEvent,
    "document.deleted.dlq": DLQEvent,
}
