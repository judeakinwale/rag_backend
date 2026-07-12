from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db

from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.rag_producer import RagProducer
from app.services.rag_service import RagService
from app.services.document_service import DocumentService
from app.services.sharepoint_service import SharepointService

from app.dependencies.shared import get_document_service


def get_sharepoint_service(request: Request) -> SharepointService:
    return request.app.state.sharepoint_service


def get_rag_producer(request: Request) -> RagProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.rag_producer(producer)


def get_rag_service(
    db=Depends(get_db),
    producer: RagProducer = Depends(get_rag_producer),
    document_service: DocumentService = Depends(get_document_service),
    sharepoint_service: SharepointService = Depends(get_sharepoint_service),
) -> RagService:
    return container.rag_service(
        db,
        rag_producer=producer,
        document_service=document_service,
        sharepoint_service=sharepoint_service,
    )
