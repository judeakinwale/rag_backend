from app.consumers import chat_consumers

TOPICS = [
    "chat.created",
    "chat.created.dlq",
    "chat.updated",
    "chat.updated.dlq",
    "chat.softdeleted",
    "chat.softdeleted.dlq",
    "chat.deleted",
    "chat.deleted.dlq",
]

HANDLERS = {
    "chat.created": chat_consumers.handle_chat_created,
    "chat.created.dlq": chat_consumers.handle_chat_created_dlq,
    "chat.updated": chat_consumers.handle_chat_updated,
    "chat.updated.dlq": chat_consumers.handle_chat_updated_dlq,
    "chat.softdeleted": chat_consumers.handle_chat_softdeleted,
    "chat.softdeleted.dlq": chat_consumers.handle_chat_softdeleted_dlq,
    "chat.deleted": chat_consumers.handle_chat_deleted,
    "chat.deleted.dlq": chat_consumers.handle_chat_deleted_dlq,
}
