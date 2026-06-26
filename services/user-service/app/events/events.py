from app.events import user_events
from rag_packages.contracts.events.shared_events import DLQEvent


EVENTS = {
    "user.created": user_events.UserCreatedEvent,
    "user.created.dlq": DLQEvent,
    "user.updated": user_events.UserUpdatedEvent,
    "user.updated.dlq": DLQEvent,
    "user.softdeleted": user_events.UserSoftDeletedEvent,
    "user.softdeleted.dlq": DLQEvent,
    "user.deleted": user_events.UserDeletedEvent,
    "user.deleted.dlq": DLQEvent,
}
