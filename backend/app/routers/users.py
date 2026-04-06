from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import ErrorResponse, User, UserCreate, UsernameAvailability

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
    return storage.create_user(db, payload.username)
