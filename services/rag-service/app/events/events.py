from app.events import chat_events as chat
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "chat.created": chat.ChatCreatedEvent,
    "chat.created.dlq": DLQEvent,
    "chat.updated": chat.ChatUpdatedEvent,
    "chat.updated.dlq": DLQEvent,
    "chat.softdeleted": chat.ChatSoftDeletedEvent,
    "chat.softdeleted.dlq": DLQEvent,
    "chat.deleted": chat.ChatDeletedEvent,
    "chat.deleted.dlq": DLQEvent,
}
