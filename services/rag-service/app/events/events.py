from app.events import rag_events, document_events
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "rag.started": rag_events.RagStartedEvent,
    "rag.started.dlq": DLQEvent,
    "rag.processing": rag_events.ProcessingStartedEvent,
    "rag.processing.dlq": DLQEvent,
    "rag.processing_completed": rag_events.ProcessingCompletedEvent,
    "rag.processing_completed.dlq": DLQEvent,
    "rag.completed": rag_events.RagCompletedEvent,
    "rag.completed.dlq": DLQEvent,
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
