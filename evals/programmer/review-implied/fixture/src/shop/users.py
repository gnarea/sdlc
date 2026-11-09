import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True)
class User:
    id: int
    email: str
    display_name: str


def get_user(connection: sqlite3.Connection, user_id: int) -> User | None:
    row = connection.execute(
        "SELECT id, email, display_name FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()
    return User(*row) if row else None
