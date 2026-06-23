from app.dto.shared_dto import BaseDTO, APIResponse


class CreateUserRequest(BaseDTO):
    email: str
    name: str
    password: str


class UpdateUserRequest(BaseDTO):
    email: str | None = None
    name: str | None = None
    password: str | None = None


class UserResponse(BaseDTO):
    id: int
    email: str
    name: str


class UserAPIResponse(APIResponse):
    data: UserResponse | None = None


class UserListAPIResponse(APIResponse):
    data: list[UserResponse] | None = None
