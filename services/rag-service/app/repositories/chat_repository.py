from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import Chat
from rag_packages.contracts.dto.chat import (
    CreateChatRequest,
    UpdateChatRequest,
)
from rag_packages.shared.database.query import QueryParams, get_model_page


class ChatRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_all(
        self, params: QueryParams | None = None
    ) -> tuple[list[Chat], int]:
        chats, count = await get_model_page(
            self.db,
            Chat,
            **params.model_dump() if params else {},
            search_fields=[
                "name",
                "file_url",
                "library_name",
                "library_id",
                "site_url",
                "parent_folder_path",
                "source",
                "file_type",
            ],
        )
        return chats, count or 0

    async def create_multiple(
        self, payloads: list[CreateChatRequest]
    ) -> list[Chat] | None:
        chats = [Chat(**payload.model_dump()) for payload in payloads]
        self.db.add_all(chats)
        return chats

    async def create(self, payload: CreateChatRequest) -> Chat | None:
        chat = Chat(**payload.model_dump())
        self.db.add(chat)
        return chat

    async def get_by_id(self, chat_id: int) -> Chat | None:
        chat = await self.db.get(Chat, chat_id)
        return chat

    async def get_by_session(self, session_id: str) -> Chat | None:
        stmt = (
            select(Chat)
            .where(Chat.session_id == session_id)
            .order_by(Chat.updated_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        chat = result.scalar_one_or_none()
        return chat

    async def get_last_user_chat(self, email: str) -> Chat | None:
        stmt = (
            select(Chat)
            .where(Chat.email == email)
            .order_by(Chat.updated_at.desc())
            .limit(1)
        )
        result = await self.db.execute(stmt)
        chat = result.scalar_one_or_none()
        return chat

    async def update(self, chat_id: int, payload: UpdateChatRequest) -> Chat | None:
        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        updates = payload.model_dump()

        for field, value in updates.items():
            setattr(chat, field, value)

        return chat

    async def delete(self, chat_id: int) -> Chat | None:
        chat = await self.get_by_id(chat_id)
        if chat is None:
            return None

        await self.db.delete(chat)

        return chat
