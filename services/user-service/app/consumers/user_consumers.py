from app.events.user_events import UserCreatedEvent, UserUpdatedEvent, UserDeletedEvent

# TODO: split this file if needed


def handle_test_event(event: dict):
    print(f"[user-service] Handling test.topic event: {event}")


def handle_user_created(event: UserCreatedEvent):
    print(f"[user-service] Handling user.created event: {event}")


def handle_user_updated(event: UserUpdatedEvent):
    print(f"[user-service] Handling user.updated event: {event}")


def handle_user_softdeleted(event: UserDeletedEvent):
    print(f"[user-service] Handling user.deleted event: {event}")


def handle_user_deleted(event: UserDeletedEvent):
    print(f"[user-service] Handling user.deleted event: {event}")
