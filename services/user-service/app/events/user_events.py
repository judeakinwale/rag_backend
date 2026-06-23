from rag_packages.contracts.events.shared_events import BaseEvent


class UserCreatedEvent(BaseEvent):
    id: int
    email: str
    name: str


class UserUpdatedEvent(UserCreatedEvent):
    updated: list[str] | None = None  # list of updated fields


class UserDeletedEvent(UserCreatedEvent):
    pass
