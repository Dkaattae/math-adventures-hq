from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import Difficulty, Grade, LeaderboardEntry, MathType

router = APIRouter(prefix="/api/leaderboard", tags=["leaderboard"])


@router.get("", response_model=list[LeaderboardEntry])
def get_leaderboard(
    mathType: Optional[MathType] = None,
    difficulty: Optional[Difficulty] = None,
    grade: Optional[Grade] = None,
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_session),
) -> list[LeaderboardEntry]:
    return storage.query_leaderboard(
        db, math_type=mathType, difficulty=difficulty, grade=grade, limit=limit
    )
