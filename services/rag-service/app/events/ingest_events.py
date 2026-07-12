from datetime import datetime
from app.dto.document_dto import DocSource
from rag_packages.contracts.events.shared_events import BaseEvent


class RagStartedEvent(BaseEvent):
    document_ids: list[int]
    source: DocSource


# track processing for each document, when all documents are processed, emit RagCompletedEvent
class ProcessingStartedEvent(BaseEvent):
    document_ids: list[int] | None = None  # for tracking and calling rag_completed
    document_id: int
    source: DocSource
    remaining_documents: int


class ProcessingCompletedEvent(BaseEvent):
    library_id: str | None = None
    document_id: int
    source: DocSource | None = None
    remaining_documents: int | None = None
    rag_initiated_at: datetime


class RagCompletedEvent(RagStartedEvent):
    pass
