from sqlalchemy.ext.asyncio import AsyncSession

from app.services.document_service import DocumentService
from app.repositories.document_repository import DocumentRepository
from app.producers.document_producer import DocumentProducer

from app.services.rag_service import RagService
from app.producers.rag_producer import RagProducer

from app.services.sharepoint_service import SharepointService, SharepointConfig

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

    def rag_producer(self, kafka_producer: KafkaProducer) -> RagProducer:
        return RagProducer(kafka_producer)

    def rag_service(
        self,
        db: AsyncSession,
        rag_producer: RagProducer | None = None,
        kafka_producer: KafkaProducer | None = None,
        document_service: DocumentService | None = None,
        sharepoint_service: SharepointService | None = None,
    ) -> RagService:
        uow = UnitOfWork(db)
        doc_repo = DocumentRepository(db)
        producer = rag_producer or RagProducer(kafka_producer)
        return RagService(
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
