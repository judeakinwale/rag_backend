from typing import Any
from datetime import datetime

# this will be moved to shared types in the future
from app.models.document import IngestStatus
from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse, APIListResponse
from rag_packages.contracts.types.shared_types import DocSource


class CreateDocumentRequest(BaseDTO):
    name: str
    file_url: str
    library_name: str | None = None
    library_id: str | None = None
    site_url: str
    parent_folder_path: str | None = None
    source: DocSource
    file_metadata: dict[str, Any] | None = None
    last_modified: str
    file_type: str
    ingest_initiated_at: datetime | None = None


class UpdateDocumentRequest(BaseDTO):
    name: str | None = None
    library_name: str | None = None
    library_id: str | None = None
    site_url: str | None = None
    parent_folder_path: str | None = None
    source: DocSource | None = None
    file_metadata: dict[str, Any] | None = None
    last_modified: str | None = None
    file_type: str | None = None


class DocumentResponse(BaseDTO):
    id: int
    name: str
    file_url: str
    library_name: str | None = None
    library_id: str | None = None
    site_url: str
    parent_folder_path: str | None = None
    source: DocSource
    file_metadata: dict[str, Any] | None = None
    last_modified: str
    file_type: str
    file_size: int
    ingest_initiated_at: datetime | None = None
    ingest_status: IngestStatus = "started"
    created_at: datetime
    created_by_id: int | None = None
    updated_at: datetime | None = None
    updated_by_id: int | None = None
    is_active: bool
    is_deleted: bool


class DocumentResponseWithB64File(DocumentResponse):
    file_b64: str
    file_sha256: str


class DocumentAPIResponse(APIResponse):
    data: DocumentResponse | None = None


class DocumentListAPIResponse(APIListResponse):
    data: list[DocumentResponse] | None = None


class DocumentAPIResponseWithB64File(APIResponse):
    data: DocumentResponseWithB64File | None = None


class DocumentListAPIResponseWithB64File(APIListResponse):
    data: list[DocumentResponseWithB64File] | None = None
