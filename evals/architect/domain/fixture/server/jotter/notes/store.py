from uuid import UUID

from jotter import db
from jotter.notes.models import Note, NoteIn


def list_notes(user_id: UUID) -> list[Note]:
    with db.connect() as connection:
        rows = connection.execute(
            "SELECT id, title, body, updated_at FROM notes"
            " WHERE user_id = %s ORDER BY updated_at DESC",
            (user_id,),
        ).fetchall()
    return [Note(**row) for row in rows]


def save_note(user_id: UUID, note_id: UUID, note: NoteIn) -> Note | None:
    """Create or overwrite the note, unless another user owns it."""
    with db.connect() as connection:
        row = connection.execute(
            """
            INSERT INTO notes (id, user_id, title, body, updated_at)
            VALUES (%s, %s, %s, %s, now())
            ON CONFLICT (id) DO UPDATE
                SET title = excluded.title, body = excluded.body, updated_at = now()
                WHERE notes.user_id = excluded.user_id
            RETURNING id, title, body, updated_at
            """,
            (note_id, user_id, note.title, note.body),
        ).fetchone()
    return Note(**row) if row else None


def delete_note(user_id: UUID, note_id: UUID) -> bool:
    with db.connect() as connection:
        result = connection.execute(
            "DELETE FROM notes WHERE id = %s AND user_id = %s",
            (note_id, user_id),
        )
    return result.rowcount == 1
