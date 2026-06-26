from fastapi import APIRouter, Depends, Request, status
from app.dto.ingest_dto import (
    IngestAPIResponse,
    CreateIngestRequest,
    UpdateIngestRequest,
    IngestListAPIResponse,
)
from app.dependencies.ingest import (
    get_ingest_service,
    get_ingest_producer,
    IngestService,
    IngestProducer,
)

router = APIRouter(prefix="/ingests", tags=["Ingests"])


@router.get(
    "",
    status_code=status.HTTP_200_OK,
    response_model=IngestListAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get all ingests",
)
async def get_ingests(
    service: IngestService = Depends(get_ingest_service),
    producer: IngestProducer = Depends(get_ingest_producer),
) -> IngestListAPIResponse:
    ingests = await service.get_ingests()
    # await producer.test({"event_msg": "get_ingests_called"})

    return IngestListAPIResponse(
        success=True,
        data=ingests,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=IngestAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Create a new ingest",
)
async def create_ingest(
    request: Request,
    body: CreateIngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestAPIResponse:
    created_ingest = await service.create_ingest(body)

    return IngestAPIResponse(
        success=True,
        data=created_ingest,
    )


@router.get(
    "/{ingest_id}",
    status_code=status.HTTP_200_OK,
    response_model=IngestAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Get a ingest by ID",
)
async def get_ingest(
    ingest_id: int, service: IngestService = Depends(get_ingest_service)
) -> IngestAPIResponse:
    ingest = await service.get_ingest_by_id(ingest_id)

    return IngestAPIResponse(
        success=True,
        data=ingest,
    )


update_kwargs = {
    "status_code": status.HTTP_200_OK,
    "response_model": IngestAPIResponse,
    "response_model_exclude_none": True,
    "response_model_exclude_unset": True,
    "summary": "Update a ingest by ID",
}


@router.patch("/{ingest_id}", **update_kwargs)
@router.put("/{ingest_id}", **update_kwargs)
async def update_ingest(
    ingest_id: int,
    body: UpdateIngestRequest,
    service: IngestService = Depends(get_ingest_service),
) -> IngestAPIResponse:
    updated_ingest = await service.update_ingest(ingest_id, body)

    return IngestAPIResponse(
        success=True,
        data=updated_ingest,
    )


@router.delete(
    "/{ingest_id}",
    status_code=status.HTTP_200_OK,
    response_model=IngestAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Delete a ingest by ID",
)
async def delete_ingest(
    ingest_id: int,
    service: IngestService = Depends(get_ingest_service),
) -> IngestAPIResponse:
    deleted_ingest = await service.delete_ingest(ingest_id)

    return IngestAPIResponse(
        success=True,
        data=deleted_ingest,
        message=f"Ingest with ID {ingest_id} has been deleted.",
    )
