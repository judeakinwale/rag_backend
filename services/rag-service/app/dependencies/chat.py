from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db
from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.chat_producer import ChatProducer
from app.repositories.chat_repository import ChatRepository
from app.services.chat_service import ChatService
from rag_packages.shared.ai.openai import OpenAIService


def get_chat_producer(request: Request) -> ChatProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.chat_producer(producer)


def get_chat_repository(db=Depends(get_db)) -> ChatRepository:
    return container.chat_repository(db)


def get_openai_service(request: Request) -> OpenAIService:
    return request.app.state.openai_service


def get_chat_service(
    db=Depends(get_db),
    producer: ChatProducer = Depends(get_chat_producer),
    openai_service: OpenAIService = Depends(get_openai_service),
) -> ChatService:
    return container.chat_service(
        db, chat_producer=producer, openai_service=openai_service
    )
