import sqlite3

from docs.models import Document, User
from docs.permissions import Permissions

MAX_QUERY_LENGTH = 200


class DocumentSearch:
    def __init__(self, connection: sqlite3.Connection, permissions: Permissions) -> None:
        self._connection = connection
        self._permissions = permissions

    def search(self, user: User, query: str) -> list[Document]:
        """Return the documents that `user` may view whose title contains `query`."""
        if MAX_QUERY_LENGTH < len(query):
            raise ValueError(f"Query exceeds the maximum length (got {len(query)} characters)")
        rows = self._connection.execute(
            "SELECT id, title, owner_id, space_id FROM documents"
            " WHERE title LIKE ? ESCAPE '\\' ORDER BY title",
            (f"%{_escape_like(query)}%",),
        ).fetchall()
        documents = [Document(*row) for row in rows]
        return [doc for doc in documents if self._permissions.can_view(user, doc)]


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
