from fastapi import Request
from app.core.container import container

from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.kafka.producers.ingest import IngestProducer


# ? maybe this is used in the near future
def get_ingest_producer(request: Request) -> IngestProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.ingest_producer(producer)
