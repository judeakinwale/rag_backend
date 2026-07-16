from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db
from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.chat_producer import ChatProducer
from app.repositories.chat_repository import ChatRepository
from app.services.chat_service import ChatService
from app.services.rag_service import RagService
from rag_packages.shared.ai.openai import OpenAIService
from rag_packages.shared.processing.qdrant import QdrantService


def get_chat_producer(request: Request) -> ChatProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.chat_producer(producer)


def get_chat_repository(db=Depends(get_db)) -> ChatRepository:
    return container.chat_repository(db)


def get_qdrant_service(request: Request) -> QdrantService:
    return request.app.state.qdrant_service


def get_openai_service(request: Request) -> OpenAIService:
    return request.app.state.openai_service


def get_chat_service(
    db=Depends(get_db),
    producer: ChatProducer = Depends(get_chat_producer),
) -> ChatService:
    return container.chat_service(db, chat_producer=producer)


def get_rag_service(
    chat_service: ChatService = Depends(get_chat_service),
    qdrant_service: QdrantService = Depends(get_qdrant_service),
    openai_service: OpenAIService = Depends(get_openai_service),
) -> RagService:
    return container.rag_service(
        chat_service=chat_service,
        qdrant_service=qdrant_service,
        openai_service=openai_service,
    )
