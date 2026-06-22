from pydantic import BaseModel
from typing import Optional


class CreateUserRequest(BaseModel):
    email: str
    name: str
    password: str


class TestUpdateUserRequest(Optional[CreateUserRequest]):
    pass


class UpdateUserRequest(BaseModel):
    email: Optional[str] = None
    name: Optional[str] = None
    password: Optional[str] = None


class UserResponse(BaseModel):
    id: int
    email: str
    name: str

    class Config:
        from_attributes = True
