from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ingest_service import IngestService
from app.repositories.ingest_repository import IngestRepository
from app.producers.ingest_producer import IngestProducer
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.kafka.producer import KafkaProducer


class Container:
    def __init__(self):
        pass

    def ingest_repository(self, db: AsyncSession) -> IngestRepository:
        return IngestRepository(db)

    def ingest_producer(self, kafka_producer: KafkaProducer) -> IngestProducer:
        return IngestProducer(kafka_producer)

    def ingest_service(
        self,
        db: AsyncSession,
        ingest_producer: IngestProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
    ) -> IngestService:
        uow = UnitOfWork(db)
        repo = IngestRepository(db)
        producer = ingest_producer or IngestProducer(kafka_producer)
        return IngestService(uow=uow, repo=repo, producer=producer)


container = Container()
