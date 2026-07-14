from __future__ import annotations
from typing import Any
from datetime import datetime
from sqlalchemy import DateTime, Index, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from rag_packages.shared.database.base import Base
from rag_packages.contracts.dto.chat import ChatMessage


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(Text, index=True, unique=True)

    # messages: Mapped[list[dict[str, Any]]] = mapped_column(
    messages: Mapped[ChatMessage] = mapped_column(JSONB, nullable=True, default=list)

    session_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True, unique=True
    )

    # url of the site the chat was on
    site_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )
    # reference to creator user id (managed in another service)
    created_by_id: Mapped[int | None] = mapped_column(
        Integer, index=True, nullable=True
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )
    updated_by_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(server_default=text("true"))
    is_deleted: Mapped[bool] = mapped_column(server_default=text("false"))

    # # ? Only required for mssql and would require removing the unique constraint on session_id
    # # Add a unique index on session_id, but only for non-null values
    # __table_args__ = (
    #     Index(
    #         "ix_chats_session_id_unique",
    #         session_id,
    #         unique=True,
    #         mssql_where=session_id.isnot(None),
    #     ),
    # )
