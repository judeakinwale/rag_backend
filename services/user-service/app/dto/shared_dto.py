from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict


class BaseDTO(BaseModel):
    model_config = SettingsConfigDict(from_attributes=True)


class APIResponse(BaseDTO):
    success: bool
    data: dict | None = None
    status: str | None = None
    message: str | None = None
