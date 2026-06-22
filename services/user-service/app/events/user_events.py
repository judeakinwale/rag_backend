from pydantic import BaseModel


class UserCreatedEvent(BaseModel):
    id: str
    email: str
    name: str


class UserUpdatedEvent(UserCreatedEvent):
    pass


class UserDeletedEvent(UserCreatedEvent):
    pass
