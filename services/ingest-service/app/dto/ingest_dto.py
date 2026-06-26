from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse
from app.models.ingest import RoleOption


class CreateIngestRequest(BaseDTO):
    email: str
    name: str
    password: str
    roles: list[RoleOption] | None = None


class UpdateIngestRequest(BaseDTO):
    email: str | None = None
    name: str | None = None
    password: str | None = None
    roles: list[RoleOption] | None = None


class IngestResponse(BaseDTO):
    id: int
    email: str
    name: str
    roles: list[RoleOption]


class IngestAPIResponse(APIResponse):
    data: IngestResponse | None = None


class IngestListAPIResponse(APIResponse):
    data: list[IngestResponse] | None = None
