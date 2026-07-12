from typing import Annotated
from fastapi import APIRouter, Depends, Request, status, Query
from app.core.config import settings
from app.dto.rag_dto import (
    RagAPIResponse,
    CreateRagRequest,
    CompleteRagRequest,
)
from app.dependencies.rag import (
    get_sharepoint_service,
    get_rag_service,
    get_rag_producer,
    SharepointService,
    RagService,
    RagProducer,
)
from rag_packages.contracts.dto.shared_dto import APIListResponse

router = APIRouter(prefix="/rag", tags=["Rag"])


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
    response_model=RagAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Start document rag from sharepoint document libraries",
)
async def start_sharepoint_rag(
    request: Request,
    body: CreateRagRequest,
    service: RagService = Depends(get_rag_service),
) -> RagAPIResponse:
    created_rag = await service.start_sharepoint_rag(body)

    return RagAPIResponse(
        success=True,
        data=created_rag,
        message="Rag started successfully",
    )


@router.post(
    "/sharepoint/complete",
    status_code=status.HTTP_200_OK,
    response_model=RagAPIResponse,
    response_model_exclude_none=True,
    response_model_exclude_unset=True,
    summary="Complete a sharepoint rag",
)
async def complete_sharepoint_rag(
    request: Request,
    body: CompleteRagRequest,
    service: RagService = Depends(get_rag_service),
) -> RagAPIResponse:
    completed_rag = await service.complete_sharepoint_rag(body)

    return RagAPIResponse(
        success=True,
        data=completed_rag,
        message="Rag completed successfully",
    )
