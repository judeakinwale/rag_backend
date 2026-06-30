from datetime import datetime

import orjson
from app.repositories.document_repository import DocumentRepository
from app.services.document_service import DocumentService
from app.services.sharepoint_service import SharepointService
from app.producers.ingest_producer import IngestProducer
from app.events.ingest_events import (
    IngestStartedEvent,
    ProcessingStartedEvent,
    IngestCompletedEvent,
)
from app.core.redis import generate_cache_key, r
from app.core.config import settings
from app.dto.document_dto import CreateDocumentRequest, DocSource
from app.dto.ingest_dto import (
    CreateIngestRequest,
    CompleteIngestRequest,
    IngestResponse,
)
from rag_packages.shared.database.uow import UnitOfWork


class IngestService:
    default_library_ids: list[str] = settings.SHAREPOINT_LIBRARY_IDS

    def __init__(
        self,
        uow: UnitOfWork,
        # # repo: IngestRepository,
        # doc_repo: DocumentRepository,
        document_service: DocumentService,
        sharepoint_service: SharepointService,
        producer: IngestProducer,
        # outbox_repo: None = None,
        document_source: DocSource = "sharepoint",
    ):
        self.uow = uow
        # # self.repo = repo
        # self.doc_repo = doc_repo
        self.document_service = document_service
        self.sharepoint_service = sharepoint_service
        self.producer = producer
        self.document_source = document_source

    def set_document_source(self, document_source: DocSource) -> None:
        self.document_source = document_source

    def sp_doc_to_create_doc_payload(
        self, sp_doc: dict, extra: dict = {}
    ) -> CreateDocumentRequest:
        return CreateDocumentRequest(
            name=sp_doc.get("name"),
            file_url=sp_doc.get("file_url"),
            library_name=sp_doc.get("library_name"),
            library_id=sp_doc.get("library_id"),
            site_url=sp_doc.get("site_url"),
            parent_folder_path=sp_doc.get("parent_folder_path"),
            file_metadata=sp_doc.get("file_metadata", {}),
            last_modified=sp_doc.get("last_modified"),
            file_type=sp_doc.get("file_type"),
            **extra,
        )

    async def start_sharepoint_ingest(
        self, payload: CreateIngestRequest
    ) -> list[IngestResponse]:
        if self.document_source != "sharepoint":
            raise ValueError(
                f"Document source is set to {self.document_source}. Cannot start SharePoint ingest."
            )

        library_ids = payload.library_ids or self.default_library_ids

        cache_key = generate_cache_key(
            f"libraries:{'.'.join(library_ids) if library_ids else 'all'}"
        )
        cached = await r.get(cache_key)

        if cached is not None:
            return IngestResponse.model_validate_json(cached)

        ingest_initiated_at = datetime.now()

        # get document from last created batch from the documents table and get the ingest_initiated_at
        last_doc = await self.document_service.get_document_in_last_batch(
            self.document_source
        )
        last_check_at = (
            last_doc.ingest_initiated_at
            if last_doc and not payload.force_reprocess_all
            else None
        )

        sp_docs: list[
            dict
        ] = await self.sharepoint_service.get_site_documents(
            library_ids=library_ids, modified_since=last_check_at
        )

        extra_payload = {
            "source": self.document_source,
            "ingest_initiated_at": ingest_initiated_at,
        }
        # TODO: change this to a forloop and use a new method in the document service to
        # check for existing documents using the file_url and library_id
        # only create new documents if they don't exist or have been modified since the last ingest_initiated_at
        # if payload.force_reprocess is True, then update existing documents with the reprocessed data
        doc_payloads = [
            self.sp_doc_to_create_doc_payload(sp_doc, extra=extra_payload)
            for sp_doc in sp_docs
        ]
        created_docs = await self.document_service.create_multiple_documents(
            doc_payloads
        )

        event = IngestStartedEvent(library_ids=library_ids, documents=created_docs)
        await self.producer.ingest_started(event)

        created_doc_ids = []
        docs_len = len(created_docs)
        for index, document in enumerate(created_docs):
            created_doc_ids.append(document.id)
            processing_event = ProcessingStartedEvent(
                document_ids=created_doc_ids,
                document_id=document.id,
                source=self.document_source,
                remaining_documents=docs_len - index - 1,
            )
            await self.producer.processing_started(processing_event)

        response = IngestResponse(library_ids=library_ids, documents=created_docs)

        # await r.set(cache_key, orjson.dumps(response.model_dump()))
        await r.set(cache_key, (response.model_dump_json()))
        return response

    async def complete_sharepoint_ingest(
        self, payload: CompleteIngestRequest
    ) -> IngestResponse | None:
        library_ids = payload.library_ids or self.default_library_ids

        # TODO: pass args from payload to get docs matching the id and equal to or more recent than the ingest_initiated_at
        documents = await self.document_service.get_documents()
        document_ids: list[str] = []

        async with self.uow:
            for document in documents:
                document_ids.append(document.id)
                document.ingest_status = "completed"

            await self.uow.session.flush()

        event = IngestCompletedEvent(
            document_ids=document_ids, source=self.document_source
        )
        await self.producer.ingest_completed(event)

        response = IngestResponse(library_ids=library_ids, documents=documents)

        return response
