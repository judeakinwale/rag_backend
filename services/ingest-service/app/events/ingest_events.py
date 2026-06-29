from app.dto.document_dto import DocSource
from rag_packages.contracts.events.shared_events import BaseEvent


class IngestStartedEvent(BaseEvent):
    document_ids: list[int]
    source: DocSource


# track processing for each document, when all documents are processed, emit IngestCompletedEvent
class ProcessingStartedEvent(BaseEvent):
    document_ids: list[int] | None = None  # for tracking and calling ingest_completed
    document_id: int
    source: DocSource
    remaining_documents: int


class IngestCompletedEvent(IngestStartedEvent):
    pass
