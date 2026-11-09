from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException

from jotter.auth import current_user_id
from jotter.notes import store
from jotter.notes.models import Note, NoteIn

router = APIRouter(prefix="/notes")


@router.get("")
def list_notes(user_id: UUID = Depends(current_user_id)) -> list[Note]:
    return store.list_notes(user_id)


@router.put("/{note_id}")
def save_note(note_id: UUID, note: NoteIn, user_id: UUID = Depends(current_user_id)) -> Note:
    saved = store.save_note(user_id, note_id, note)
    if saved is None:
        raise HTTPException(status_code=404)
    return saved


@router.delete("/{note_id}", status_code=204)
def delete_note(note_id: UUID, user_id: UUID = Depends(current_user_id)) -> None:
    if not store.delete_note(user_id, note_id):
        raise HTTPException(status_code=404)
