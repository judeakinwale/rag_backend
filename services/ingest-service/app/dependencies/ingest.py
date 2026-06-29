from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db

from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.ingest_producer import IngestProducer
from app.services.ingest_service import IngestService
from app.services.document_service import DocumentService
from app.services.sharepoint_service import SharepointService

from app.dependencies.shared import get_document_service


def get_sharepoint_service(request: Request) -> SharepointService:
    return request.app.state.sharepoint_service


def get_ingest_producer(request: Request) -> IngestProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.ingest_producer(producer)


def get_ingest_service(
    db=Depends(get_db),
    producer: IngestProducer = Depends(get_ingest_producer),
    document_service: DocumentService = Depends(get_document_service),
    sharepoint_service: SharepointService = Depends(get_sharepoint_service),
) -> IngestService:
    return container.ingest_service(
        db,
        ingest_producer=producer,
        document_service=document_service,
        sharepoint_service=sharepoint_service,
    )
