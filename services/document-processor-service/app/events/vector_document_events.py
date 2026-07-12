from datetime import datetime
from rag_packages.contracts.events.shared_events import BaseEvent
# from app.dto.document_dto import DocSource


class VectorDocumentCreatedEvent(BaseEvent):
    id: int
    doc_id: int
    chunk_id: int
    file_name: str
    # source: DocSource
    initiated_at: datetime


class VectorDocumentProcessedEvent(VectorDocumentCreatedEvent):
    metadata: dict | None = None


# TODO: confirm this is used
class VectorDocumentUpdatedEvent(VectorDocumentCreatedEvent):
    # updated: list[str] | None = None  # list of updated fields
    pass


# TODO: confirm this is used
class VectorDocumentSoftDeletedEvent(VectorDocumentCreatedEvent):
    pass


class VectorDocumentDeletedEvent(VectorDocumentCreatedEvent):
    pass
