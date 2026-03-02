from __future__ import annotations

from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    """Tag response model."""
    id: UUID = Field(..., description="Tag UUID")
    name: str = Field(..., description="Tag display name")
    color: Optional[str] = Field(None, description="Optional hex color string for UI")

    model_config = {"from_attributes": True}


class NoteBase(BaseModel):
    """Common editable fields for notes."""
    title: str = Field("", max_length=200, description="Note title (<= 200 characters)")
    content: str = Field("", description="Note content (free text)")


class NoteCreate(NoteBase):
    """Create note payload."""
    is_pinned: bool = Field(False, description="Whether the note is pinned")
    is_favorite: bool = Field(False, description="Whether the note is marked as favorite")
    tag_ids: List[UUID] = Field(default_factory=list, description="Optional list of tag IDs to assign")


class NoteUpdate(BaseModel):
    """Update note payload (all optional)."""
    title: Optional[str] = Field(None, max_length=200, description="Note title (<= 200 characters)")
    content: Optional[str] = Field(None, description="Note content")
    is_pinned: Optional[bool] = Field(None, description="Whether the note is pinned")
    is_favorite: Optional[bool] = Field(None, description="Whether the note is marked as favorite")
    tag_ids: Optional[List[UUID]] = Field(None, description="If provided, replaces tag assignment with these tag IDs")


class NoteOut(NoteBase):
    """Note response model."""
    id: UUID = Field(..., description="Note UUID")
    is_pinned: bool = Field(..., description="Pinned flag")
    is_favorite: bool = Field(..., description="Favorite flag")
    created_at: datetime = Field(..., description="Created timestamp")
    updated_at: datetime = Field(..., description="Updated timestamp")
    tags: List[TagOut] = Field(default_factory=list, description="Tags assigned to this note")

    model_config = {"from_attributes": True}


class TagCreate(BaseModel):
    """Create tag payload."""
    name: str = Field(..., min_length=1, max_length=50, description="Tag name (unique case-insensitive after trim/lower)")
    color: Optional[str] = Field(None, description="Optional hex color string for UI")


class TagUpdate(BaseModel):
    """Update tag payload."""
    name: Optional[str] = Field(None, min_length=1, max_length=50, description="Tag name")
    color: Optional[str] = Field(None, description="Optional hex color string for UI")
