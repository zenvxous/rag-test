from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, Enum, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, generate_uuid

if TYPE_CHECKING:
    from app.db.models.document_chunks import DocumentChunk


class Status(enum.Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    INDEXED = "INDEXED"
    ERROR = "ERROR"

class Document(Base):
    __tablename__ = "documents"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=generate_uuid)
    filename: Mapped[str] = mapped_column(String(256), nullable=False)
    minio_key: Mapped[str] = mapped_column(String(256), nullable=False, unique=True)
    file_size: Mapped[int | None] = mapped_column(nullable=True)
    mime_type: Mapped[str] = mapped_column(String(64), default="application/pdf", nullable=False)
    checksum: Mapped[str | None] = mapped_column(String(128), nullable=True, unique=True)
    status: Mapped[Status] = mapped_column(
        Enum(Status, name="status_enum"),
        default=Status.PENDING,
        server_default="PENDING",
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
		nullable=False,
    )
    indexed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    chunks: Mapped[list[DocumentChunk]] = relationship(
        "DocumentChunk",
        back_populates="document",
        lazy="selectin",
        passive_deletes=True,
    )

    __table_args__ = (
        CheckConstraint(
            """
            (status = 'ERROR' AND error_message IS NOT NULL)
            OR
            (status <> 'ERROR' AND error_message IS NULL)
            """,
            name="ck_documents_error_message_matches_status",
        ),
        CheckConstraint(
            """
            (status = 'INDEXED' AND indexed_at IS NOT NULL)
            OR
            (status <> 'INDEXED' AND indexed_at IS NULL)
            """,
            name="ck_documents_indexed_at_matches_status",
        ),
    )
