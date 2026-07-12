# from typing import Annotated
# from fastapi import APIRouter, Depends, Request, status, Query
# from app.dto.document_dto import (
#     DocumentAPIResponse,
#     CreateDocumentRequest,
#     UpdateDocumentRequest,
#     DocumentListAPIResponse,
# )
# from app.dependencies.document import (
#     get_document_service,
#     get_document_producer,
#     DocumentService,
#     DocumentProducer,
# )
# from app.dependencies.ingest import get_sharepoint_service, SharepointService
# from rag_packages.shared.database.query import QueryParams


# router = APIRouter(prefix="/documents", tags=["Documents"])


# # TODO: these routes should not be needed
# @router.get(
#     "",
#     status_code=status.HTTP_200_OK,
#     response_model=DocumentListAPIResponse,
#     response_model_exclude_none=True,
#     response_model_exclude_unset=True,
#     summary="Get all documents",
# )
# async def get_documents(
#     query: Annotated[QueryParams, Query()],
#     service: DocumentService = Depends(get_document_service),
#     producer: DocumentProducer = Depends(get_document_producer),
# ) -> DocumentListAPIResponse:
#     documents, count = await service.get_documents(query)

#     return DocumentListAPIResponse(
#         success=True,
#         data=documents,
#         count=count,
#     )


# @router.post(
#     "",
#     status_code=status.HTTP_201_CREATED,
#     response_model=DocumentAPIResponse,
#     response_model_exclude_none=True,
#     response_model_exclude_unset=True,
#     summary="Create a new document",
# )
# async def create_document(
#     request: Request,
#     body: CreateDocumentRequest,
#     service: DocumentService = Depends(get_document_service),
# ) -> DocumentAPIResponse:
#     created_document = await service.create_document(body)

#     return DocumentAPIResponse(
#         success=True,
#         data=created_document,
#     )


# @router.get(
#     "/{document_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=DocumentAPIResponse,
#     response_model_exclude_none=True,
#     response_model_exclude_unset=True,
#     summary="Get a document by ID",
# )
# async def get_document(
#     document_id: int,
#     include_file: bool = Query(False),
#     service: DocumentService = Depends(
#         get_document_service,
#     ),
#     sharepoint_service: SharepointService = Depends(get_sharepoint_service),
# ) -> DocumentAPIResponse:
#     document = await service.get_document_by_id(document_id)

#     if include_file:
#         file_info = await sharepoint_service.get_file(document.file_url)
#         print({"file_info": file_info})
#         document.file_b64 = file_info["b64"]
#         document.file_size = file_info["size"]
#         document.file_sha256 = file_info["sha256"]

#     return DocumentAPIResponse(
#         success=True,
#         data=document,
#     )


# update_kwargs = {
#     "status_code": status.HTTP_200_OK,
#     "response_model": DocumentAPIResponse,
#     "response_model_exclude_none": True,
#     "response_model_exclude_unset": True,
#     "summary": "Update a document by ID",
# }


# @router.patch("/{document_id}", **update_kwargs)
# @router.put("/{document_id}", **update_kwargs)
# async def update_document(
#     document_id: int,
#     body: UpdateDocumentRequest,
#     service: DocumentService = Depends(get_document_service),
# ) -> DocumentAPIResponse:
#     updated_document = await service.update_document(document_id, body)

#     return DocumentAPIResponse(
#         success=True,
#         data=updated_document,
#     )


# @router.delete(
#     "/{document_id}",
#     status_code=status.HTTP_200_OK,
#     response_model=DocumentAPIResponse,
#     response_model_exclude_none=True,
#     response_model_exclude_unset=True,
#     summary="Delete a document by ID",
# )
# async def delete_document(
#     document_id: int,
#     service: DocumentService = Depends(get_document_service),
# ) -> DocumentAPIResponse:
#     deleted_document = await service.delete_document(document_id)

#     return DocumentAPIResponse(
#         success=True,
#         data=deleted_document,
#         message=f"Document with ID {document_id} has been deleted.",
#     )
