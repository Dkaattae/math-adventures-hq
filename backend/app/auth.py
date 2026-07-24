"""Bearer-token auth for the per-player endpoints.

Signup, login and PIN reset hand back a session token; the endpoints that
expose one player's history require it. Everything else (leaderboard,
quizzes) stays open — the leaderboard is public by design.
"""
from __future__ import annotations

from typing import Optional

from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from . import storage
from .db import get_session
from .models import ErrorResponse


def unauthorized(message: str) -> HTTPException:
    return HTTPException(
        status_code=401,
        detail=ErrorResponse(code="unauthorized", message=message).model_dump(),
        headers={"WWW-Authenticate": "Bearer"},
    )


def bearer_token(authorization: Optional[str] = Header(default=None)) -> Optional[str]:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer":
        return None
    return token.strip() or None


def require_self(
    username: str,
    token: Optional[str] = Depends(bearer_token),
    db: Session = Depends(get_session),
) -> str:
    """The `{username}` in the path must be the token's own account."""
    if token is None:
        raise unauthorized("Log in to see this player's progress.")
    owner = storage.session_username(db, token)
    if owner is None:
        raise unauthorized("Your login expired — pop your PIN in again!")
    if owner.lower() != username.lower():
        raise unauthorized("That's someone else's progress — you can only see your own.")
    return owner
