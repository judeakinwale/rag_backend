from app.events.user_events import UserCreatedEvent, UserDeletedEvent, UserUpdatedEvent


EVENTS = {
    "user.created": UserCreatedEvent,
    "user.updated": UserUpdatedEvent,
    "user.deleted": UserDeletedEvent,
}
