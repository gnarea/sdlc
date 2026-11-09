import sqlite3

from docs.models import Document, User


class Permissions:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    def can_view(self, user: User, doc: Document) -> bool:
        """Return whether `user` may view `doc`: they own it, or they belong to its space."""
        if doc.owner_id == user.id:
            return True
        membership = self._connection.execute(
            "SELECT 1 FROM space_members WHERE space_id = ? AND user_id = ?",
            (doc.space_id, user.id),
        ).fetchone()
        return membership is not None
