from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db
from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.ingest_producer import IngestProducer
from app.repositories.ingest_repository import IngestRepository
from app.services.ingest_service import IngestService


def get_ingest_producer(request: Request) -> IngestProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.ingest_producer(producer)


def get_ingest_repository(db=Depends(get_db)) -> IngestRepository:
    return container.ingest_repository(db)


def get_ingest_service(
    db=Depends(get_db), producer: IngestProducer = Depends(get_ingest_producer)
) -> IngestService:
    return container.ingest_service(db, ingest_producer=producer)
