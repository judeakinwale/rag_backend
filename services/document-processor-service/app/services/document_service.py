import orjson
from app.repositories.document_repository import DocumentRepository
from app.producers.document_producer import DocumentProducer
from app.events.document_events import (
    DocumentCreatedEvent,
    DocumentUpdatedEvent,
    DocumentDeletedEvent,
)
from app.models.document import Document
from app.core.redis import generate_cache_key, r
from app.dto.document_dto import (
    CreateDocumentRequest,
    UpdateDocumentRequest,
    DocumentResponse,
)
from rag_packages.shared.database.uow import UnitOfWork
from rag_packages.contracts.types.document import DocSource
from rag_packages.shared.database.query import QueryParams


class DocumentService:
    def __init__(
        self,
        uow: UnitOfWork,
        repo: DocumentRepository,
        producer: DocumentProducer,
        # outbox_repo: None = None,
    ):
        self.uow = uow
        self.repo = repo
        self.producer = producer

    async def get_documents(
        self, params: QueryParams | None = None
    ) -> tuple[list[DocumentResponse], int]:
        cache_key = generate_cache_key(str("all"))
        cached = await r.get(cache_key)

        if cached is not None:
            try:
                document_arr = orjson.loads(
                    cached
                )  # Ensure the cached data is valid JSON
                return [
                    DocumentResponse.model_validate_json(document)
                    for document in document_arr
                ]

            except orjson.JSONDecodeError:
                print(
                    f"[document-service] Failed to decode cached data for key {cache_key}. Invalidating cache."
                )
                await r.delete(cache_key)  # invalidate corrupted cache

        documents, count = await self.repo.get_all(params)
        valid_documents = [
            DocumentResponse.model_validate(document) for document in documents
        ]

        await r.set(cache_key, orjson.dumps(valid_documents))
        return valid_documents

    async def create_multiple_documents(
        self, payloads: list[CreateDocumentRequest]
    ) -> list[DocumentResponse] | None:
        async with self.uow:
            documents: list[Document] = await self.repo.create_multiple(payloads)

            # ensure the documents are persisted and
            await self.uow.session.flush()
            # access the persisted documents' ids before committing and sending the events
            document_ids = [document.id for document in documents]
            print(f"Created documents with IDs: {document_ids}")

        events = [
            DocumentCreatedEvent.model_validate(document) for document in documents
        ]

        for event in events:
            await self.producer.document_created(event)

        return [DocumentResponse.model_validate(document) for document in documents]

    async def create_document(self, payload: CreateDocumentRequest) -> DocumentResponse:
        async with self.uow:
            document: Document = await self.repo.create(payload)

            # ensure the document is persisted and
            await self.uow.session.flush()
            # access the persisted document's id before committing and sending the event
            document_id = document.id
            print(f"Created document with ID: {document_id}, details: {document}")

        event = DocumentCreatedEvent.model_validate(document)
        await self.producer.document_created(event)

        return DocumentResponse.model_validate(document)

    async def get_document_by_id(self, document_id: int) -> DocumentResponse | None:
        cache_key = generate_cache_key(str(document_id))
        cached = await r.get(cache_key)

        if cached is not None:
            return DocumentResponse.model_validate_json(cached)

        document = await self.repo.get_by_id(document_id)
        if document is None:
            return None

        valid_document = DocumentResponse.model_validate(document)

        await r.set(cache_key, valid_document.model_dump_json())
        return valid_document

    async def get_document_in_last_batch(
        self, source: DocSource
    ) -> DocumentResponse | None:
        cache_key = generate_cache_key(str(source))
        cached = await r.get(cache_key)

        if cached is not None:
            return DocumentResponse.model_validate_json(cached)

        document = await self.repo.get_last_batch_document(source)
        if document is None:
            return None

        valid_document = DocumentResponse.model_validate(document)

        await r.set(cache_key, valid_document.model_dump_json())
        return valid_document

    async def update_document(
        self, document_id: int, payload: UpdateDocumentRequest
    ) -> DocumentResponse | None:
        async with self.uow:
            document: Document | None = await self.repo.update(document_id, payload)
            if document is None:
                return None

        event = DocumentUpdatedEvent.model_validate(document)
        event.updated = list(payload.model_dump(exclude_unset=True).keys())
        await self.producer.document_updated(event)

        return DocumentResponse.model_validate(document)

    async def delete_document(self, document_id: int) -> DocumentResponse | None:
        async with self.uow:
            document: Document | None = await self.repo.delete(document_id)
            if document is None:
                return None

        event = DocumentDeletedEvent.model_validate(document)
        await self.producer.document_deleted(event)

        return DocumentResponse.model_validate(document)
