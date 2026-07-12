from fastapi import Request
from app.core.container import container

from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.processing.qdrant import QdrantService
from rag_packages.shared.processing.document_processor import DocumentProcessor

from app.producers.vector_document_producer import VectorDocumentProducer


async def get_vector_document_producer() -> VectorDocumentProducer:
    return await container.vector_document_producer()


def get_qdrant_service() -> QdrantService:
    return container.qdrant_service


def get_document_processor_service() -> DocumentProcessor:
    return container.document_processor_service


# _____________________________________________________________________________________


def get_vector_document_producer_web(request: Request) -> VectorDocumentProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.vector_document_producer(producer)


def get_qdrant_service_web(request: Request) -> QdrantService:
    return request.app.state.qdrant_service


def get_document_processor_service_web(request: Request) -> DocumentProcessor:
    return request.app.state.document_processor_service
