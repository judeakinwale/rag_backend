from datetime import datetime
from rag_packages.contracts.events.shared_events import BaseEvent


class ChatCreatedEvent(BaseEvent):
    id: int
    email: str | None = None
    session_id: str | None = None
    created_at: datetime


class ChatUpdatedEvent(ChatCreatedEvent):
    updated: list[str] | None = None  # list of updated fields


class ChatSoftDeletedEvent(ChatCreatedEvent):
    pass


class ChatDeletedEvent(ChatCreatedEvent):
    pass
