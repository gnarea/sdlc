from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class NoteIn(BaseModel):
    title: str = Field(max_length=200)
    body: str = Field(max_length=100_000)


class Note(NoteIn):
    id: UUID
    updated_at: datetime
