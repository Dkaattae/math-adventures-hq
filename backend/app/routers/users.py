from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import (
    ErrorResponse,
    SuggestedLevel,
    User,
    UserCreate,
    UserLogin,
    UsernameAvailability,
    UserStats,
)

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/check", response_model=UsernameAvailability)
def check_username(
    username: str = Query(min_length=1, max_length=20),
    db: Session = Depends(get_session),
) -> UsernameAvailability:
    return UsernameAvailability(
        username=username, available=not storage.user_exists(db, username)
    )


@router.post("", response_model=User, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> User:
    if storage.user_exists(db, payload.username):
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                code="username_taken",
                message=f"Username '{payload.username}' is already taken.",
            ).model_dump(),
        )
    return storage.create_user(db, payload.username, payload.pin)


@router.post("/login", response_model=User)
def login(payload: UserLogin, db: Session = Depends(get_session)) -> User:
    user = storage.check_login(db, payload.username, payload.pin)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                code="invalid_login",
                message="That name and PIN don't match. Try again!",
            ).model_dump(),
        )
    return user


@router.get("/{username}/stats", response_model=UserStats)
def user_stats(username: str, db: Session = Depends(get_session)) -> UserStats:
    # No auth gate: stats are derived from the public leaderboard, and a
    # player with no history simply gets zeros.
    return storage.query_user_stats(db, username)


@router.get("/{username}/suggested-level", response_model=Optional[SuggestedLevel])
def suggested_level(username: str, db: Session = Depends(get_session)) -> Optional[SuggestedLevel]:
    return storage.suggest_level(db, username)
