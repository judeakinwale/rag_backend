from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.user import User
from app.dto.user_dto import CreateUserRequest, UpdateUserRequest
from rag_packages.shared.auth.security import hash_password
from rag_packages.shared.database.query import QueryParams, get_model_page


class UserRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self, params: QueryParams | None = None
    ) -> tuple[list[User], int]:
        users, count = await get_model_page(
            self.db,
            User,
            **params.model_dump() if params else {},
            search_fields=["email", "name"],
        )
        return users, count or 0

    async def create(self, payload: CreateUserRequest) -> User | None:
        user_data = payload.model_dump()
        user_data["password"] = hash_password(payload.password)
        user = User(**user_data)
        self.db.add(user)

        return user

    async def get_by_id(self, user_id: int) -> User | None:
        user = await self.db.get(User, user_id)
        return user

    async def get_by_email(self, email: str) -> User | None:
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        user = result.scalar_one_or_none()
        return user

    async def update(self, user_id: int, payload: UpdateUserRequest) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        if "password" in updates and updates["password"] is not None:
            updates["password"] = hash_password(updates["password"])

        for field, value in updates.items():
            setattr(user, field, value)

        return user

    async def delete(self, user_id: int) -> User | None:
        user = await self.get_by_id(user_id)
        if user is None:
            return None

        await self.db.delete(user)

        return user
