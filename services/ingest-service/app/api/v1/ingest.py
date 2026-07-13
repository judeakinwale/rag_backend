from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Query
from app.core.config import settings
from rag_packages.contracts.dto.ingest import (
    IngestAPIResponse,
    CreateIngestRequest,
    CompleteIngestRequest,
)
from app.dependencies.ingest import (
    get_sharepoint_service,
    get_ingest_service,
    get_ingest_producer,
    SharepointService,
    IngestService,
    IngestProducer,
)
from rag_packages.contracts.dto.shared_dto import APIListResponse

router = APIRouter(prefix="/ingest", tags=["Ingest"])


@router.get(
    "/sharepoint/libraries",
    status_code=status.HTTP_200_OK,
    response_model=APIListResponse,
)
async def get_sharepoint_libraries(
    request: Request,
    sharepoint_service: SharepointService = Depends(get_sharepoint_service),
):
    libraries = await sharepoint_service.get_site_document_libraries()
    return APIListResponse(
        success=True,
        data=libraries,
        count=len(libraries),
        message="SharePoint libraries retrieved successfully",
    )


@router.get(
    "/sharepoint/documents",
    status_code=status.HTTP_200_OK,
    response_model=APIListResponse,
)
async def get_sharepoint_documents(
    request: Request,
    library_ids: Annotated[list[str] | None, Query()] = None,
    sharepoint_service: SharepointService = Depends(get_sharepoint_service),
):
    library_ids = library_ids or settings.SHAREPOINT_LIBRARY_IDS
    documents = await sharepoint_service.get_site_documents(library_ids)
    return APIListResponse(
        success=True,
        data=documents,
        count=len(documents),
        message="SharePoint documents retrieved successfully",
    )


@router.post(
    "/sharepoint",
    status_code=status.HTTP_200_OK,
    response_model=IngestAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Start document ingest from sharepoint document libraries",
)
async def start_sharepoint_ingest(
    request: Request,
    body: CreateIngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestAPIResponse:
    created_ingest = await service.start_sharepoint_ingest(body)

    return IngestAPIResponse(
        success=True,
        data=created_ingest,
        message="Ingest started successfully",
    )


@router.post(
    "/sharepoint/complete",
    status_code=status.HTTP_200_OK,
    response_model=IngestAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Complete a sharepoint ingest",
)
async def complete_sharepoint_ingest(
    request: Request,
    body: CompleteIngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestAPIResponse:
    completed_ingest = await service.complete_sharepoint_ingest(body)

    return IngestAPIResponse(
        success=True,
        data=completed_ingest,
        message="Ingest completed successfully",
    )
