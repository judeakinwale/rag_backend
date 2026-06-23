from pydantic import BaseModel
from pydantic_settings import SettingsConfigDict


class BaseEvent(BaseModel):
    model_config = SettingsConfigDict(from_attributes=True)
