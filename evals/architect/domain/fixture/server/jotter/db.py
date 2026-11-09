import os
from collections.abc import Iterator
from contextlib import contextmanager
from uuid import UUID

import psycopg
from psycopg.rows import dict_row


@contextmanager
def connect() -> Iterator[psycopg.Connection]:
    with psycopg.connect(os.environ["DATABASE_URL"], row_factory=dict_row) as connection:
        yield connection


def user_id_for_session(token: str) -> UUID | None:
    with connect() as connection:
        row = connection.execute(
            "SELECT user_id FROM sessions"
            " WHERE token_hash = sha256(convert_to(%s, 'UTF8')) AND expires_at > now()",
            (token,),
        ).fetchone()
    return row["user_id"] if row else None
