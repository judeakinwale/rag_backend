# from app.core.config import settings
from app.consumers import user_consumers
# from rag_packages.shared.kafka.consumer import KafkaConsumer


# "user.created.dlq": user_consumers.handle_user_created,
# "user.updated.dlq": user_consumers.handle_user_updated,
# "user.deleted.dlq": user_consumers.handle_user_deleted,

# HIGH_WATERMARK = 9990
# LOW_WATERMARK = 9000
# QUEUE_MAXSIZE = 10000

TOPICS = [
    "test.topic",
    "user.created",
    "user.updated",
    "user.softdeleted",
    "user.deleted",
]

HANDLERS = {
    "test.topic": user_consumers.handle_test_event,
    "user.created": user_consumers.handle_user_created,
    "user.updated": user_consumers.handle_user_updated,
    "user.softdeleted": user_consumers.handle_user_softdeleted,
    "user.deleted": user_consumers.handle_user_deleted,
}

# consumer = KafkaConsumer(
#     topics=TOPICS,
#     handlers=HANDLERS,
#     dlq_producer=producer,
#     bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#     service_name=settings.APP_NAME,
# )
