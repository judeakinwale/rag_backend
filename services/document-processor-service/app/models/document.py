from __future__ import annotations
from typing import Any, Literal, TypeAlias
from datetime import datetime
from sqlalchemy import DateTime, Integer, String, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from rag_packages.shared.database.base import Base
from rag_packages.contracts.types.shared_types import DocSource


IngestStatus: TypeAlias = Literal["started", "processing", "completed", "failed"]


# document references stored in the database
class Document(Base):
    __tablename__ = "documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    file_url: Mapped[str] = mapped_column(Text, index=True, unique=True)

    # specific to files from sharepoint libraries
    library_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    library_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, index=True
    )

    # root url of the document source
    site_url: Mapped[str] = mapped_column(Text)

    # path relative to site url
    parent_folder_path: Mapped[str] = mapped_column(Text)

    source: Mapped[DocSource] = mapped_column(String(255), index=True)
    file_metadata: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    last_modified: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    file_type: Mapped[str] = mapped_column(String(255))
    file_size: Mapped[int] = mapped_column(Integer)  # in bytes

    # track when the ingest batch processing this document was initiated
    # (for use when checking for untracked documents)
    ingest_initiated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ingest_status: Mapped[IngestStatus] = mapped_column(
        String(50), server_default="started"
    )
    # track when the batch before the one that processed this document, was initiated on the service
    # (for use when forcing reprocessing of documents processed in this document's batch)
    prev_batch_ingest_init: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

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
