from rag_packages.contracts.dto.shared_dto import BaseDTO, APIResponse, APIListResponse
from app.models.user import RoleOption


class CreateUserRequest(BaseDTO):
    email: str
    name: str
    password: str
    roles: list[RoleOption] | None = None


class UpdateUserRequest(BaseDTO):
    email: str | None = None
    name: str | None = None
    password: str | None = None
    roles: list[RoleOption] | None = None


class UserResponse(BaseDTO):
    id: int
    email: str
    name: str
    roles: list[RoleOption]


class UserAPIResponse(APIResponse):
    data: UserResponse | None = None


class UserListAPIResponse(APIListResponse):
    data: list[UserResponse] | None = None
