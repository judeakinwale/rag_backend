# from app.core.config import settings
from app.consumers import ingest_consumers
# from rag_packages.shared.kafka.consumer import KafkaConsumer


TOPICS = [
    "test.topic",
    "ingest.created",
    "ingest.created.dlq",
    "ingest.updated",
    "ingest.updated.dlq",
    "ingest.softdeleted",
    "ingest.softdeleted.dlq",
    "ingest.deleted",
    "ingest.deleted.dlq",
]

HANDLERS = {
    "test.topic": ingest_consumers.handle_test_event,
    "ingest.created": ingest_consumers.handle_ingest_created,
    "ingest.created.dlq": ingest_consumers.handle_ingest_created_dlq,
    "ingest.updated": ingest_consumers.handle_ingest_updated,
    "ingest.updated.dlq": ingest_consumers.handle_ingest_updated_dlq,
    "ingest.softdeleted": ingest_consumers.handle_ingest_softdeleted,
    "ingest.softdeleted.dlq": ingest_consumers.handle_ingest_softdeleted_dlq,
    "ingest.deleted": ingest_consumers.handle_ingest_deleted,
    "ingest.deleted.dlq": ingest_consumers.handle_ingest_deleted_dlq,
}

# consumer = KafkaConsumer(
#     topics=TOPICS,
#     handlers=HANDLERS,
#     dlq_producer=producer,
#     bootstrap_servers=settings.KAFKA_BOOTSTRAP_SERVERS,
#     service_name=settings.APP_NAME,
# )
