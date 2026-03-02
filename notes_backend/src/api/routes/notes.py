from __future__ import annotations

from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import delete, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models import Note, NoteTag, Tag
from src.schemas import NoteCreate, NoteOut, NoteUpdate

router = APIRouter(prefix="/notes", tags=["notes"])


async def _get_note_or_404(db: AsyncSession, note_id: UUID) -> Note:
    note = await db.get(Note, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note


async def _replace_note_tags(db: AsyncSession, note_id: UUID, tag_ids: List[UUID]) -> None:
    # Remove existing
    await db.execute(delete(NoteTag).where(NoteTag.note_id == note_id))

    if not tag_ids:
        return

    # Validate tags exist
    result = await db.execute(select(Tag.id).where(Tag.id.in_(tag_ids)))
    found_ids = {row[0] for row in result.all()}
    missing = [str(tid) for tid in tag_ids if tid not in found_ids]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unknown tag_ids: {', '.join(missing)}",
        )

    # Insert join rows
    for tid in tag_ids:
        db.add(NoteTag(note_id=note_id, tag_id=tid))


# PUBLIC_INTERFACE
@router.get(
    "",
    response_model=List[NoteOut],
    summary="List notes",
    description="List notes, optionally filtered by tag_id and/or favorites, with pinned-first sorting.",
    operation_id="list_notes",
)
async def list_notes(
    tag_id: Optional[UUID] = Query(None, description="Filter notes that have this tag"),
    favorites_only: bool = Query(False, description="If true, only return favorites"),
    q: Optional[str] = Query(None, description="Optional search query (uses full-text index where possible)"),
    limit: int = Query(50, ge=1, le=200, description="Max number of notes to return"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    db: AsyncSession = Depends(get_db),
) -> List[NoteOut]:
    stmt = select(Note).distinct()

    if tag_id:
        stmt = stmt.join(NoteTag, NoteTag.note_id == Note.id).where(NoteTag.tag_id == tag_id)

    if favorites_only:
        stmt = stmt.where(Note.is_favorite.is_(True))

    if q:
        # Use to_tsvector('simple', title || ' ' || content) @@ plainto_tsquery('simple', :q)
        stmt = stmt.where(
            text(
                "to_tsvector('simple', coalesce(notes.title,'') || ' ' || coalesce(notes.content,'')) "
                "@@ plainto_tsquery('simple', :q)"
            )
        ).params(q=q)

    stmt = stmt.order_by(Note.is_pinned.desc(), Note.created_at.desc()).limit(limit).offset(offset)

    result = await db.execute(stmt)
    return result.scalars().unique().all()


# PUBLIC_INTERFACE
@router.post(
    "",
    response_model=NoteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a note",
    description="Create a note, optionally pinned/favorite and with initial tag assignment.",
    operation_id="create_note",
)
async def create_note(payload: NoteCreate, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = Note(
        title=payload.title,
        content=payload.content,
        is_pinned=payload.is_pinned,
        is_favorite=payload.is_favorite,
    )
    db.add(note)
    try:
        await db.flush()  # get note.id
        if payload.tag_ids:
            await _replace_note_tags(db, note.id, payload.tag_ids)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid note data") from e

    await db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.get(
    "/{note_id}",
    response_model=NoteOut,
    summary="Get a note",
    description="Fetch a single note by ID.",
    operation_id="get_note",
)
async def get_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    return note


# PUBLIC_INTERFACE
@router.patch(
    "/{note_id}",
    response_model=NoteOut,
    summary="Update a note",
    description="Update note fields. If tag_ids is provided, it replaces the note's tag assignment.",
    operation_id="update_note",
)
async def update_note(note_id: UUID, payload: NoteUpdate, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)

    if payload.title is not None:
        note.title = payload.title
    if payload.content is not None:
        note.content = payload.content
    if payload.is_pinned is not None:
        note.is_pinned = payload.is_pinned
    if payload.is_favorite is not None:
        note.is_favorite = payload.is_favorite

    try:
        if payload.tag_ids is not None:
            await _replace_note_tags(db, note.id, payload.tag_ids)
        await db.commit()
    except IntegrityError as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid update") from e

    await db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a note",
    description="Delete a note by ID (note_tags join rows are cascade-deleted).",
    operation_id="delete_note",
)
async def delete_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> None:
    note = await _get_note_or_404(db, note_id)
    await db.delete(note)
    await db.commit()
    return None


# PUBLIC_INTERFACE
@router.post(
    "/{note_id}/pin",
    response_model=NoteOut,
    summary="Pin a note",
    description="Set is_pinned=true for the note.",
    operation_id="pin_note",
)
async def pin_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    note.is_pinned = True
    await db.commit()
    await db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.post(
    "/{note_id}/unpin",
    response_model=NoteOut,
    summary="Unpin a note",
    description="Set is_pinned=false for the note.",
    operation_id="unpin_note",
)
async def unpin_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    note.is_pinned = False
    await db.commit()
    await db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.post(
    "/{note_id}/favorite",
    response_model=NoteOut,
    summary="Favorite a note",
    description="Set is_favorite=true for the note.",
    operation_id="favorite_note",
)
async def favorite_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    note.is_favorite = True
    await db.commit()
    await db.refresh(note)
    return note


# PUBLIC_INTERFACE
@router.post(
    "/{note_id}/unfavorite",
    response_model=NoteOut,
    summary="Unfavorite a note",
    description="Set is_favorite=false for the note.",
    operation_id="unfavorite_note",
)
async def unfavorite_note(note_id: UUID, db: AsyncSession = Depends(get_db)) -> NoteOut:
    note = await _get_note_or_404(db, note_id)
    note.is_favorite = False
    await db.commit()
    await db.refresh(note)
    return note
