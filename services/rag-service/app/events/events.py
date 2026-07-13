from rag_packages.contracts.events import ingest, document
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "ingest.started": ingest.IngestStartedEvent,
    "ingest.started.dlq": DLQEvent,
    "ingest.processing": ingest.ProcessingStartedEvent,
    "ingest.processing.dlq": DLQEvent,
    "ingest.processing.completed": ingest.ProcessingCompletedEvent,
    "ingest.processing.completed.dlq": DLQEvent,
    "ingest.processing.failed": ingest.ProcessingFailedEvent,
    "ingest.processing.failed.dlq": DLQEvent,
    "ingest.completed": ingest.IngestCompletedEvent,
    "ingest.completed.dlq": DLQEvent,
    # ________________________________________________________________
    "document.created": document.DocumentCreatedEvent,
    "document.created.dlq": DLQEvent,
    "document.processed": document.DocumentProcessedEvent,
    "document.processed.dlq": DLQEvent,
    "document.updated": document.DocumentUpdatedEvent,
    "document.updated.dlq": DLQEvent,
    "document.softdeleted": document.DocumentSoftDeletedEvent,
    "document.softdeleted.dlq": DLQEvent,
    "document.deleted": document.DocumentDeletedEvent,
    "document.deleted.dlq": DLQEvent,
}
