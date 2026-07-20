from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import (
    ErrorResponse,
    PinReset,
    SuggestedLevel,
    User,
    UserCreate,
    UserCreated,
    UserLogin,
    UsernameAvailability,
    UserStats,
)

router = APIRouter(prefix="/api/users", tags=["users"])


def _locked_response(err: storage.AccountLockedError) -> HTTPException:
    minutes = max(1, err.retry_after_seconds // 60 + (1 if err.retry_after_seconds % 60 else 0))
    return HTTPException(
        status_code=429,
        detail=ErrorResponse(
            code="too_many_attempts",
            message=f"Too many tries! Take a break and try again in about {minutes} "
            f"minute{'s' if minutes != 1 else ''}.",
        ).model_dump(),
        headers={"Retry-After": str(err.retry_after_seconds)},
    )


@router.get("/check", response_model=UsernameAvailability)
def check_username(
    username: str = Query(min_length=1, max_length=20),
    db: Session = Depends(get_session),
) -> UsernameAvailability:
    return UsernameAvailability(
        username=username, available=not storage.user_exists(db, username)
    )


@router.post("", response_model=UserCreated, status_code=201)
def create_user(payload: UserCreate, db: Session = Depends(get_session)) -> UserCreated:
    if storage.user_exists(db, payload.username):
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                code="username_taken",
                message=f"Username '{payload.username}' is already taken.",
            ).model_dump(),
        )
    recovery_code = storage.generate_recovery_code()
    user = storage.create_user(db, payload.username, payload.pin, recovery_code=recovery_code)
    # The plaintext code exists only in this response — only its hash is stored.
    return UserCreated(username=user.username, createdAt=user.createdAt, recoveryCode=recovery_code)


@router.post("/login", response_model=User)
def login(payload: UserLogin, db: Session = Depends(get_session)) -> User:
    try:
        user = storage.check_login(db, payload.username, payload.pin)
    except storage.AccountLockedError as err:
        raise _locked_response(err)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                code="invalid_login",
                message="That name and PIN don't match. Try again!",
            ).model_dump(),
        )
    return user


@router.post("/reset-pin", response_model=User)
def reset_pin(payload: PinReset, db: Session = Depends(get_session)) -> User:
    try:
        user = storage.reset_pin(db, payload.username, payload.recoveryCode, payload.newPin)
    except storage.AccountLockedError as err:
        raise _locked_response(err)
    if user is None:
        raise HTTPException(
            status_code=401,
            detail=ErrorResponse(
                code="invalid_recovery_code",
                message="That rescue code doesn't match. Check your note and try again!",
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
