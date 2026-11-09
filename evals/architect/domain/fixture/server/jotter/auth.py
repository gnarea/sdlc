from uuid import UUID

from fastapi import Header, HTTPException

from jotter import db


def current_user_id(authorization: str = Header()) -> UUID:
    scheme, _, token = authorization.partition(" ")
    user_id = db.user_id_for_session(token) if scheme == "Bearer" and token else None
    if user_id is None:
        raise HTTPException(status_code=401)
    return user_id
