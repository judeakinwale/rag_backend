from sqlalchemy.ext.asyncio import AsyncSession
from app.services.chat_service import ChatService
from app.repositories.chat_repository import ChatRepository
from app.producers.chat_producer import ChatProducer

from rag_packages.shared.kafka.producers.ingest import IngestProducer
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.kafka.producer import KafkaProducer
from rag_packages.shared.ai.openai import OpenAIService


class Container:
    def __init__(self):
        pass

    def chat_repository(self, db: AsyncSession) -> ChatRepository:
        return ChatRepository(db)

    def chat_producer(self, kafka_producer: KafkaProducer) -> ChatProducer:
        return ChatProducer(kafka_producer)

    def chat_service(
        self,
        db: AsyncSession,
        chat_producer: ChatProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
        openai_service: OpenAIService | None = None,
    ) -> ChatService:
        uow = UnitOfWork(db)
        repo = ChatRepository(db)
        producer = chat_producer or ChatProducer(kafka_producer)
        return ChatService(
            uow=uow, repo=repo, producer=producer, openai_service=openai_service
        )

    # _____________________________________________________________________________

    def ingest_producer(self, kafka_producer: KafkaProducer) -> IngestProducer:
        return IngestProducer(kafka_producer)


container = Container()
