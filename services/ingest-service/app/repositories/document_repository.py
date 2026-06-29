from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.document import Document
from app.dto.document_dto import DocSource, CreateDocumentRequest, UpdateDocumentRequest


class DocumentRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    # TODO: add logic to document repo get all to allow for filtering by model properties,
    # an array of ids, search using a query, and sorting by model properties,
    # specifying a limit and offset for pagination and a count in the response
    async def get_all(self) -> list[Document]:
        stmt = select(Document)
        result = await self.db.execute(stmt)
        documents = result.scalars().all()
        return documents

    async def create_multiple(
        self, payloads: list[CreateDocumentRequest]
    ) -> list[Document] | None:
        documents = [Document(**payload.model_dump()) for payload in payloads]
        self.db.add_all(documents)
        return documents

    async def create(self, payload: CreateDocumentRequest) -> Document | None:
        document = Document(**payload.model_dump())
        self.db.add(document)
        return document

    async def get_by_id(self, document_id: int) -> Document | None:
        document = await self.db.get(Document, document_id)
        return document

    # get a document from the last ingest batch for a specified source
    async def get_last_batch_document(self, source: DocSource) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.source == source)
            .order_by(Document.ingest_initiated_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        document = result.scalar_one_or_none()
        return document

    async def update(
        self, document_id: int, payload: UpdateDocumentRequest
    ) -> Document | None:
        document = await self.get_by_id(document_id)
        if document is None:
            return None

        updates = payload.model_dump()

        for field, value in updates.items():
            setattr(document, field, value)

        return document

    async def delete(self, document_id: int) -> Document | None:
        document = await self.get_by_id(document_id)
        if document is None:
            return None

        await self.db.delete(document)

        return document
