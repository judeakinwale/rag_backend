from app.consumers import ingest_consumers, vector_document_consumers

# ? ingest topics are shared with the ingest service

TOPICS = [
    "vector_document.created",
    "vector_document.created.dlq",
    "vector_document.processed",
    "vector_document.processed.dlq",
    "vector_document.updated",
    "vector_document.updated.dlq",
    "vector_document.softdeleted",
    "vector_document.softdeleted.dlq",
    "vector_document.deleted",
    "vector_document.deleted.dlq",
    # ________________________
    "ingest.started",
    "ingest.started.dlq",
    "ingest.processing",
    "ingest.processing.dlq",
    "ingest.processing.completed",
    "ingest.processing.completed.dlq",
    "ingest.processing.failed",
    "ingest.processing.failed.dlq",
    "ingest.completed",
    "ingest.completed.dlq",
]

HANDLERS = {
    "vector_document.created": vector_document_consumers.handle_vector_document_created,
    "vector_document.created.dlq": vector_document_consumers.handle_vector_document_created_dlq,
    "vector_document.processed": vector_document_consumers.handle_vector_document_processed,
    "vector_document.processed.dlq": vector_document_consumers.handle_vector_document_processed_dlq,
    "vector_document.updated": vector_document_consumers.handle_vector_document_updated,
    "vector_document.updated.dlq": vector_document_consumers.handle_vector_document_updated_dlq,
    "vector_document.softdeleted": vector_document_consumers.handle_vector_document_softdeleted,
    "vector_document.softdeleted.dlq": vector_document_consumers.handle_vector_document_softdeleted_dlq,
    "vector_document.deleted": vector_document_consumers.handle_vector_document_deleted,
    "vector_document.deleted.dlq": vector_document_consumers.handle_vector_document_deleted_dlq,
    # __________________________________________________________________________
    "ingest.started": ingest_consumers.handle_ingest_started,
    "ingest.started.dlq": ingest_consumers.handle_ingest_started_dlq,
    "ingest.processing": ingest_consumers.handle_processing_started,
    "ingest.processing.dlq": ingest_consumers.handle_processing_started_dlq,
    "ingest.processing.completed": ingest_consumers.handle_processing_completed,
    "ingest.processing.completed.dlq": ingest_consumers.handle_processing_completed_dlq,
    "ingest.processing.failed": ingest_consumers.handle_processing_failed,
    "ingest.processing.failed.dlq": ingest_consumers.handle_processing_failed_dlq,
    "ingest.completed": ingest_consumers.handle_ingest_completed,
    "ingest.completed.dlq": ingest_consumers.handle_ingest_completed_dlq,
}
