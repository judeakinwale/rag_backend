from app.consumers import document_consumers, ingest_consumers


TOPICS = [
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
    # ________________________
    "document.created",
    "document.created.dlq",
    "document.processed",
    "document.processed.dlq",
    "document.updated",
    "document.updated.dlq",
    "document.softdeleted",
    "document.softdeleted.dlq",
    "document.deleted",
    "document.deleted.dlq",
]

HANDLERS = {
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
    # __________________________________________________________________________
    "document.created": document_consumers.handle_document_created,
    "document.created.dlq": document_consumers.handle_document_created_dlq,
    "document.processed": document_consumers.handle_document_processed,
    "document.processed.dlq": document_consumers.handle_document_processed_dlq,
    "document.updated": document_consumers.handle_document_updated,
    "document.updated.dlq": document_consumers.handle_document_updated_dlq,
    "document.softdeleted": document_consumers.handle_document_softdeleted,
    "document.softdeleted.dlq": document_consumers.handle_document_softdeleted_dlq,
    "document.deleted": document_consumers.handle_document_deleted,
    "document.deleted.dlq": document_consumers.handle_document_deleted_dlq,
}
