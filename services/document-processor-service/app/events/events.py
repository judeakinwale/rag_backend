from app.events import vector_document_events
from rag_packages.contracts.events import ingest
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "vector_document.created": vector_document_events.VectorDocumentCreatedEvent,
    "vector_document.created.dlq": DLQEvent,
    "vector_document.processed": vector_document_events.VectorDocumentProcessedEvent,
    "vector_document.processed.dlq": DLQEvent,
    "vector_document.updated": vector_document_events.VectorDocumentUpdatedEvent,
    "vector_document.updated.dlq": DLQEvent,
    "vector_document.softdeleted": vector_document_events.VectorDocumentSoftDeletedEvent,
    "vector_document.softdeleted.dlq": DLQEvent,
    "vector_document.deleted": vector_document_events.VectorDocumentDeletedEvent,
    "vector_document.deleted.dlq": DLQEvent,
    # __________________________________________________________________________
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
}
