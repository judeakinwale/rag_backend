from __future__ import annotations

from enum import StrEnum

from sqlalchemy import DateTime, Enum, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column, relationship
from rag_packages.shared.database.base import Base


class RoleOption(StrEnum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"


role_enum = Enum(RoleOption, name="user_role", native_enum=False)


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(255))
    password: Mapped[str] = mapped_column(String(255))

    roles: Mapped[list[RoleOption]] = mapped_column(
        ARRAY(role_enum),
        default=lambda: [RoleOption.USER],
        nullable=False,
    )

    created_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    created_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by: Mapped[User | None] = relationship(
        remote_side=[id],
        back_populates="created_users",
        foreign_keys=[created_by_id],
    )
    created_users: Mapped[list[User]] = relationship(
        back_populates="created_by",
        foreign_keys=[created_by_id],
    )

    updated_at: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    updated_by_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    updated_by: Mapped[User | None] = relationship(
        remote_side=[id],
        back_populates="updated_users",
        foreign_keys=[updated_by_id],
    )
    updated_users: Mapped[list[User]] = relationship(
        back_populates="updated_by",
        foreign_keys="User.updated_by_id",
    )

    is_active: Mapped[bool] = mapped_column(default=True)
    is_deleted: Mapped[bool] = mapped_column(default=False)
