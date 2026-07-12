from datetime import datetime
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse
from app.dto.document_dto import DocumentResponse


# NOTE: library_ids is optional because it is only relevant for sharepoint and
# if none if provided for sharepoint, it gets all documents from all libraries


class CreateRagRequest(BaseDTO):
    library_ids: list[str] | None = None
    # process newly modified documents and reprocess tracked documents from the last rag batch
    force_reprocess: bool = False
    # process newly modified documents and reprocess all documents
    force_reprocess_all: bool = False


class CompleteRagRequest(BaseDTO):
    library_ids: list[str] | None = None
    document_ids: list[int]
    rag_initiated_at: datetime


class RagResponse(BaseDTO):
    library_ids: list[str] | None = None
    documents: list[DocumentResponse]


class RagAPIResponse(APIResponse):
    data: RagResponse | None = None
