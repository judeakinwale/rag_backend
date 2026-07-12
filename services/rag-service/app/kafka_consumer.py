from app.consumers import document_consumers, rag_consumers


TOPICS = [
    "rag.started",
    "rag.started.dlq",
    "rag.processing",
    "rag.processing.dlq",
    "rag.processing_completed",
    "rag.processing_completed.dlq",
    "rag.completed",
    "rag.completed.dlq",
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
    "rag.started": rag_consumers.handle_rag_started,
    "rag.started.dlq": rag_consumers.handle_rag_started_dlq,
    "rag.processing": rag_consumers.handle_processing_started,
    "rag.processing.dlq": rag_consumers.handle_processing_started_dlq,
    "rag.completed": rag_consumers.handle_rag_completed,
    "rag.completed.dlq": rag_consumers.handle_rag_completed_dlq,
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
