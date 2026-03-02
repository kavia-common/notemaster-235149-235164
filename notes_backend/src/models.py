from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base for ORM models."""
    pass


class NoteTag(Base):
    """Join table between notes and tags."""
    __tablename__ = "note_tags"

    note_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("notes.id", ondelete="CASCADE"),
        primary_key=True,
    )
    tag_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    )
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Note(Base):
    """Notes table."""
    __tablename__ = "notes"
    __table_args__ = (
        CheckConstraint("char_length(title) <= 200", name="notes_title_len"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    title: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    content: Mapped[str] = mapped_column(Text, nullable=False, server_default="")
    is_pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    tags: Mapped[List["Tag"]] = relationship(
        secondary="note_tags",
        back_populates="notes",
        lazy="selectin",
    )


class Tag(Base):
    """Tags table."""
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("char_length(name) BETWEEN 1 AND 50", name="tags_name_len"),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())
    name: Mapped[str] = mapped_column(Text, nullable=False)
    # normalized_name is a generated column in DB; we include it read-only here for filters.
    normalized_name: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    color: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    notes: Mapped[List[Note]] = relationship(
        secondary="note_tags",
        back_populates="tags",
        lazy="selectin",
    )
