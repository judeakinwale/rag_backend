from fastapi import APIRouter, Depends, Request, status
from app.dto.ingest_dto import (
    IngestAPIResponse,
    CreateIngestRequest,
    CompleteIngestRequest,
)
from app.dependencies.ingest import (
    get_ingest_service,
    get_ingest_producer,
    IngestService,
    IngestProducer,
)

router = APIRouter(prefix="/ingest", tags=["Ingest"])


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
