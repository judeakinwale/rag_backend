from rag_packages.contracts.events.shared_events import BaseEvent


class IngestCreatedEvent(BaseEvent):
    id: int
    email: str
    name: str


class IngestUpdatedEvent(IngestCreatedEvent):
    updated: list[str] | None = None  # list of updated fields


class IngestSoftDeletedEvent(IngestCreatedEvent):
    pass


class IngestDeletedEvent(IngestCreatedEvent):
    pass
