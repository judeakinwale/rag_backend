from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db
from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.document_producer import DocumentProducer
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService


def get_document_producer(request: Request) -> DocumentProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.document_producer(producer)


def get_document_repository(db=Depends(get_db)) -> DocumentRepository:
    return container.document_repository(db)


def get_document_service(
    db=Depends(get_db), producer: DocumentProducer = Depends(get_document_producer)
) -> DocumentService:
    return container.document_service(db, document_producer=producer)
