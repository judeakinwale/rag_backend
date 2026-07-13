from sqlalchemy.ext.asyncio import AsyncSession
from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.producers.document_producer import DocumentProducer
from app.services.ingest_service import IngestService
from app.services.sharepoint_service import SharepointService, SharepointConfig


from rag_packages.shared.kafka.producers.ingest import IngestProducer
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.shared.kafka.producer import KafkaProducer


class Container:
    def __init__(self):
        pass

    def document_repository(self, db: AsyncSession) -> DocumentRepository:
        return DocumentRepository(db)

    def document_producer(self, kafka_producer: KafkaProducer) -> DocumentProducer:
        return DocumentProducer(kafka_producer)

    def document_service(
        self,
        db: AsyncSession,
        document_producer: DocumentProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
    ) -> DocumentService:
        uow = UnitOfWork(db)
        repo = DocumentRepository(db)
        producer = document_producer or DocumentProducer(kafka_producer)
        return DocumentService(uow=uow, repo=repo, producer=producer)

    # _____________________________________________________________________________

    def ingest_producer(self, kafka_producer: KafkaProducer) -> IngestProducer:
        return IngestProducer(kafka_producer)

    def ingest_service(
        self,
        db: AsyncSession,
        ingest_producer: IngestProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
        document_service: DocumentService | None = None,
        sharepoint_service: SharepointService | None = None,
    ) -> IngestService:
        uow = UnitOfWork(db)
        doc_repo = DocumentRepository(db)
        producer = ingest_producer or IngestProducer(kafka_producer)
        return IngestService(
            uow=uow,
            doc_repo=doc_repo,
            producer=producer,
            document_service=document_service,
            document_source="sharepoint",  # default source, can be changed later
            sharepoint_service=sharepoint_service,
        )

    # _____________________________________________________________________________

    def sharepoint_service(self, config: SharepointConfig) -> SharepointService:
        return SharepointService(config=config)


container = Container()
