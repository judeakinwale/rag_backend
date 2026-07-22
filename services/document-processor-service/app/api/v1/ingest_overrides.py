import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Query
from app.core.config import settings
from app.dependencies.document_processor import get_qdrant_service, QdrantService
from app.consumers.ingest_consumer_utils import IngestConsumerUtils
from rag_packages.shared.database.query import QueryParams
from rag_packages.contracts.dto.vector_document import APIListResponse
from rag_packages.contracts.events.ingest import (
    ProcessingStartedEvent,
    ProcessingCompletedEvent,
)

from rag_packages.shared.exception.exception import (
    BadRequestException,
)

logger = logging.getLogger(__name__)
service_name = settings.APP_NAME

router = APIRouter(prefix="/ingest-overrides", tags=["Ingest Overrides"])

consumer_utils = IngestConsumerUtils()

# ! Override the default event based processing behavior
# For testing


@router.get(
    "/document/chunks",
    status_code=status.HTTP_200_OK,
    response_model=APIListResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get all documents",
)
async def get_document_chunks(
    query: Annotated[QueryParams, Query()],
    qdrant_service: QdrantService = Depends(get_qdrant_service),
) -> APIListResponse:
    try:
        points = await qdrant_service.search(
            query.query, filters=query.filters, limit=query.limit
        )
    except Exception as e:
        raise BadRequestException(
            f"[{service_name}] Error fetching document chunks: {e}"
        )

    return APIListResponse(
        success=True,
        data=points,
        count=len(points),
    )


@router.post(
    "/document/process",
    status_code=status.HTTP_201_CREATED,
    response_model=APIListResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new document",
)
async def process_document_override(
    request: Request,
    body: ProcessingStartedEvent,
) -> APIListResponse:
    try:
        data = await consumer_utils.process_event_document(body)
    except Exception as e:
        await consumer_utils.trigger_processing_failed(body, error=e)
        raise BadRequestException(f"[{service_name}] Error processing document: {e}")

    return APIListResponse(
        success=True,
        data=data,
        count=len(data),
    )


@router.post(
    "/document/processed",
    status_code=status.HTTP_201_CREATED,
    response_model=APIListResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new document",
)
async def document_processed_override(
    request: Request,
    body: ProcessingCompletedEvent,
) -> APIListResponse:

    try:
        data = await consumer_utils.event_document_processed(body)
    except Exception as e:
        await consumer_utils.trigger_processing_failed(body, error=e)
        raise BadRequestException(f"[{service_name}] Error processing document: {e}")

    return APIListResponse(
        success=True,
        data=data,
        count=len(data) if data else 0,
    )
