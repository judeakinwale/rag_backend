from sqlalchemy.ext.asyncio import AsyncSession
from app.services.user_service import UserService
from app.repositories.user_repository import UserRepository
from app.producers.user_producer import UserProducer
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.kafka.producer import KafkaProducer


class Container:
    def __init__(self):
        pass

    def user_repository(self, db: AsyncSession) -> UserRepository:
        return UserRepository(db)

    def user_producer(self, kafka_producer: KafkaProducer) -> UserProducer:
        return UserProducer(kafka_producer)

    def user_service(
        self,
        db: AsyncSession,
        user_producer: UserProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
    ) -> UserService:
        uow = UnitOfWork(db)
        repo = UserRepository(db)
        producer = user_producer or UserProducer(kafka_producer)
        return UserService(uow=uow, repo=repo, producer=producer)


container = Container()
