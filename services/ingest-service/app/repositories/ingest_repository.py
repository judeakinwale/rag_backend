from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.ingest import Ingest
from app.dto.ingest_dto import CreateIngestRequest, UpdateIngestRequest
from rag_packages.shared.auth.security import hash_password


class IngestRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(self) -> list[Ingest]:
        stmt = select(Ingest)
        result = await self.db.execute(stmt)
        ingests = result.scalars().all()
        return ingests

    async def create(self, payload: CreateIngestRequest) -> Ingest | None:
        ingest_data = payload.model_dump()
        ingest_data["password"] = hash_password(payload.password)
        ingest = Ingest(**ingest_data)
        self.db.add(ingest)

        return ingest

    async def get_by_id(self, ingest_id: int) -> Ingest | None:
        ingest = await self.db.get(Ingest, ingest_id)
        return ingest

    async def get_by_email(self, email: str) -> Ingest | None:
        stmt = select(Ingest).where(Ingest.email == email)
        result = await self.db.execute(stmt)
        ingest = result.scalar_one_or_none()
        return ingest

    async def update(self, ingest_id: int, payload: UpdateIngestRequest) -> Ingest | None:
        ingest = await self.get_by_id(ingest_id)
        if ingest is None:
            return None

        updates = payload.model_dump(exclude_unset=True)
        if "password" in updates and updates["password"] is not None:
            updates["password"] = hash_password(updates["password"])

        for field, value in updates.items():
            setattr(ingest, field, value)

        return ingest

    async def delete(self, ingest_id: int) -> Ingest | None:
        ingest = await self.get_by_id(ingest_id)
        if ingest is None:
            return None

        await self.db.delete(ingest)

        return ingest
