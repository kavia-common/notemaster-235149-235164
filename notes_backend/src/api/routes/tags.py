from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models import Tag
from src.schemas import TagCreate, TagOut, TagUpdate

router = APIRouter(prefix="/tags", tags=["tags"])


async def _get_tag_or_404(db: AsyncSession, tag_id: UUID) -> Tag:
    tag = await db.get(Tag, tag_id)
    if not tag:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tag not found")
    return tag


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[TagOut],
    summary="List tags",
    description="List tags ordered by name. Supports simple name prefix filtering.",
    operation_id="list_tags",
)
async def list_tags(
    q: Optional[str] = Query(None, description="Optional name prefix filter (case-insensitive)"),
    limit: int = Query(200, ge=1, le=500, description="Max number of tags to return"),
    db: AsyncSession = Depends(get_db),
) -> List[TagOut]:
    stmt = select(Tag)
    if q:
        stmt = stmt.where(Tag.normalized_name.ilike(f"{q.strip().lower()}%"))
    stmt = stmt.order_by(Tag.normalized_name.asc()).limit(limit)

    result = await db.execute(stmt)
    return result.scalars().all()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=TagOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a tag",
    description="Create a new tag. Tag name is unique case-insensitively via normalized_name.",
    operation_id="create_tag",
)
async def create_tag(payload: TagCreate, db: AsyncSession = Depends(get_db)) -> TagOut:
    tag = Tag(name=payload.name.strip(), color=payload.color)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag already exists (case-insensitive)",
        ) from e

    await db.refresh(tag)
    return tag


# PUBLIC_INTERFACE
@router.patch(
    "/{tag_id}",
    response_model=TagOut,
    summary="Update a tag",
    description="Update tag name and/or color.",
    operation_id="update_tag",
)
async def update_tag(tag_id: UUID, payload: TagUpdate, db: AsyncSession = Depends(get_db)) -> TagOut:
    tag = await _get_tag_or_404(db, tag_id)
    if payload.name is not None:
        tag.name = payload.name.strip()
    if payload.color is not None:
        tag.color = payload.color

    try:
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Tag name conflicts with an existing tag",
        ) from e

    await db.refresh(tag)
    return tag


# PUBLIC_INTERFACE
@router.delete(
    "/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a tag",
    description="Delete a tag. Join rows in note_tags are cascade-deleted.",
    operation_id="delete_tag",
)
async def delete_tag(tag_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    tag = await _get_tag_or_404(db, tag_id)
    await db.delete(tag)
    await db.commit()
    return None
