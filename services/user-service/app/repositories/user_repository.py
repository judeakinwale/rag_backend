from sqlalchemy import select

# from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.dto.user_dto import CreateUserRequest, UpdateUserRequest


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, payload: CreateUserRequest) -> User | None:
        user = User(**payload.model_dump())
        await self.db.add(user)

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        stmt = select(User).where(User.id == user_id)
        user = await self.db.execute(stmt).scalar_one_or_none()

        user = await self.db.get(User, user_id)
        if not user:
            return None

        return user

    async def update(self, user_id: int, payload: UpdateUserRequest) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        updates = payload.model_dump(exclude_unset=True)

        for field, value in updates.items():
            setattr(user, field, value)

        return user

    async def delete(self, user_id: int) -> User | None:
        user = await self.get_by_id(user_id)
        if not user:
            return None

        await self.db.delete(user)

        return user
