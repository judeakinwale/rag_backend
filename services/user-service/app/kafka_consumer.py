# from app.core.config import settings
from app.consumers import user_consumers
# from rag_packages.shared.kafka.consumer import KafkaConsumer


TOPICS = [
    "test.topic",
    "user.created",
    "user.created.dlq",
    "user.updated",
    "user.updated.dlq",
    "user.softdeleted",
    "user.softdeleted.dlq",
    "user.deleted",
    "user.deleted.dlq",
]

HANDLERS = {
    "test.topic": user_consumers.handle_test_event,
    "user.created": user_consumers.handle_user_created,
    "user.created.dlq": user_consumers.handle_user_created_dlq,
    "user.updated": user_consumers.handle_user_updated,
    "user.updated.dlq": user_consumers.handle_user_updated_dlq,
    "user.softdeleted": user_consumers.handle_user_softdeleted,
    "user.softdeleted.dlq": user_consumers.handle_user_softdeleted_dlq,
    "user.deleted": user_consumers.handle_user_deleted,
    "user.deleted.dlq": user_consumers.handle_user_deleted_dlq,
}

# consumer = KafkaConsumer(
#     topics=TOPICS,
#     handlers=HANDLERS,
#     dlq_producer=producer,
#     bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#     service_name=settings.APP_NAME,
# )
