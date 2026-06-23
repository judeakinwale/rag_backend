from fastapi import Depends, Request
from app.core.container import container
from app.core.db import get_db
from rag_packages.shared.kafka.producer import KafkaProducer
from app.producers.user_producer import UserProducer
from app.repositories.user_repository import UserRepository
from app.services.user_service import UserService


def get_user_producer(request: Request) -> UserProducer:
    producer: KafkaProducer = request.app.state.kafka_producer
    return container.user_producer(producer)


def get_user_repository(db=Depends(get_db)) -> UserRepository:
    return container.user_repository(db)


def get_user_service(
    db=Depends(get_db), producer: UserProducer = Depends(get_user_producer)
) -> UserService:
    return container.user_service(db, user_producer=producer)
