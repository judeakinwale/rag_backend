import httpx
import logging
from datetime import datetime, UTC
from typing import Any
from app.core.container import container
from app.core.config import settings
from rag_packages.contracts.events import ingest as ingest_events
from rag_packages.contracts.dto.document import DocumentAPIResponse, DocumentResponse
from rag_packages.contracts.dto.vector_document import (
    CreateVectorDocumentRequest,
    VectorDocumentFileMetadata,
)
from rag_packages.contracts.dto.document_processor import ProcessedChunk
from rag_packages.contracts.dto.ingest import CompleteIngestRequest

# from rag_packages.shared.processing.qdrant import UpdateResult
from rag_packages.shared.exception.exception import ValidationException


logger = logging.getLogger(__name__)


class IngestConsumerUtils:
    def __init__(self):
        self.ingest_origin = settings.INGEST_SERVICE_ORIGIN

    def _chunk_to_vector_document(
        self, chunk: ProcessedChunk, document: DocumentResponse
    ):
        file_metadata = VectorDocumentFileMetadata(
            source=document.source,
            file_url=document.file_url,
            library_name=document.library_name,
            file_type=document.file_type,
            file_size=document.file_size,
            last_modified=document.last_modified,
        )

        return CreateVectorDocumentRequest(
            doc_id=document.id,
            chunk_id=chunk.index,
            file_name=document.name,
            text=chunk.text,
            details=chunk.details,
            metadata=chunk.metadata,
            file_metadata=file_metadata,
            initiated_at=document.ingest_initiated_at,
        )

    # chunk and process a document into vector embeddings / documents and store them in qdrant
    async def process_event_document(
        self, event: ingest_events.ProcessingStartedEvent
    ) -> list[Any]:
        ingest_producer = await container.ingest_producer()

        # fetch document with details and base64 file from ingest-service
        document_url = f"{self.ingest_origin}/api/v1/documents/{event.document_id}?include_file=true"
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(document_url)
            response.raise_for_status()
            document_response = DocumentAPIResponse.model_validate(response.json())
            document = document_response.data

        if document is None:
            err_msg = f"Document with id: {event.document_id} not found."
            failed_event = ingest_events.ProcessingFailedEvent(
                document_id=event.document_id,
                source=event.source,
                remaining_documents=event.remaining_documents,
                ingest_failed_at=datetime.now(tz=UTC),
                error=err_msg,
            )
            await ingest_producer.processing_failed(failed_event)
            raise ValidationException(err_msg)

        # process document (extract text, chunk text, generate embeddings)
        processed_document = await container.document_processor_service.process(
            file_b64=document.file_b64,
            file_type=document.file_type,
            file_name=document.name,
        )

        # store each processed document chunk in qdrant
        vector_documents = [
            self._chunk_to_vector_document(chunk, document=document)
            for chunk in processed_document.chunks
        ]
        update_result = await container.qdrant_service.add_chunks_to_collection(
            vector_documents
        )

        # send processing completed signal? to ingest-service consumer for the single document
        #     - using http to POST https://ingest-service/api/v1/ingest/completed
        #     # - using ingest_producer.ingest_completed(event) -> "ingest.completed",
        completed_event = ingest_events.ProcessingCompletedEvent(
            library_id=document.library_id,
            document_id=document.id,
            source=document.source,
            remaining_documents=event.remaining_documents,
            ingest_initiated_at=document.ingest_initiated_at,
        )
        await ingest_producer.processing_completed(completed_event)

        logger.info(f"vector collection added chunks: {update_result}")

        return update_result

    async def event_document_processed(
        self,
        event: ingest_events.ProcessingCompletedEvent,
    ) -> None:

        # trigger processing complete on ingest service
        endpoint = f"{self.ingest_origin}/api/v1/ingest/sharepoint/complete"

        payload = CompleteIngestRequest(
            library_ids=[event.library_id],
            document_ids=[event.document_id],
            ingest_initiated_at=event.ingest_initiated_at,
        )

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=payload.model_dump(mode="json"),
            )
            response.raise_for_status()
            documents = response.json()

        logger.info(f"processed documents db references updated: {documents}")

    async def trigger_processing_failed(
        self,
        event: ingest_events.ProcessingStartedEvent,
        error: Exception | str | None = None,
        initiated_at: datetime | None = None,
    ) -> None:

        # the failed event has been triggered so raise the same error
        if isinstance(error, ValidationException):
            logger.error(
                f"Validation error processing document {event.document_id}: {error}"
            )
            raise error

        # trigger processing failed event on ingest service
        failed_event = ingest_events.ProcessingFailedEvent(
            document_id=event.document_id,
            source=event.source,
            remaining_documents=event.remaining_documents,
            ingest_initiated_at=initiated_at,
            ingest_failed_at=datetime.now(UTC),
            error=str(error) if error else None,
        )

        ingest_producer = await container.ingest_producer()
        await ingest_producer.processing_failed(failed_event)

        if isinstance(error, Exception):
            raise error

        error = str(error) if error else "unknown error"
        raise ValidationException(
            f"Processing failed for document {event.document_id}: {error}"
        )
