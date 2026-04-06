"""Database-backed repository. Same interface the routers used for the
previous in-memory store, but now talks to SQLAlchemy."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from .db_models import LeaderboardRow, QuizResultRow, QuizRow, UserRow
from .models import (
    Difficulty,
    Grade,
    LeaderboardEntry,
    MathType,
    QuestionInternal,
    QuestionResult,
    QuizResult,
    User,
)

__all__ = [
    "format_time",
    "user_exists",
    "create_user",
    "save_quiz",
    "get_quiz",
    "quiz_questions",
    "mark_submitted",
    "add_leaderboard_entry",
    "query_leaderboard",
    "reset",
]


def format_time(seconds: int) -> str:
    m, s = divmod(seconds, 60)
    return f"{m}m {s:02d}s"


# ---------- serialization helpers ----------

def _question_to_json(q: QuestionInternal) -> dict:
    return {
        "id": q.id,
        "question": q.question,
        "correctAnswer": q.correctAnswer,
        "explanation": q.explanation,
    }


def _question_from_json(d: dict) -> QuestionInternal:
    return QuestionInternal(**d)


def _result_item_to_json(r: QuestionResult) -> dict:
    return r.model_dump()


# ---------- users ----------

def user_exists(db: Session, username: str) -> bool:
    return db.scalar(select(UserRow).where(UserRow.username_lower == username.lower())) is not None


def create_user(db: Session, username: str) -> User:
    row = UserRow(
        username=username,
        username_lower=username.lower(),
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return User(username=row.username, createdAt=row.created_at)


# ---------- quizzes ----------

def save_quiz(
    db: Session,
    quiz_id: UUID,
    username: str,
    grade: Grade,
    math_type: MathType,
    difficulty: Difficulty,
    questions: list[QuestionInternal],
) -> QuizRow:
    row = QuizRow(
        id=quiz_id,
        username=username,
        grade=grade.value,
        math_type=math_type.value,
        difficulty=difficulty.value,
        questions_json=[_question_to_json(q) for q in questions],
        created_at=datetime.now(timezone.utc),
        submitted=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def get_quiz(db: Session, quiz_id: UUID) -> Optional[QuizRow]:
    return db.get(QuizRow, quiz_id)


def quiz_questions(row: QuizRow) -> list[QuestionInternal]:
    return [_question_from_json(d) for d in row.questions_json]


def mark_submitted(db: Session, quiz_id: UUID, result: QuizResult) -> None:
    quiz = db.get(QuizRow, quiz_id)
    assert quiz is not None
    quiz.submitted = True
    db.add(
        QuizResultRow(
            quiz_id=quiz_id,
            username=result.username,
            score=result.score,
            total=result.total,
            time_used_seconds=result.timeUsedSeconds,
            badge=result.badge,
            results_json=[_result_item_to_json(r) for r in result.results],
            submitted_at=result.submittedAt,
        )
    )
    db.commit()


# ---------- leaderboard ----------

def add_leaderboard_entry(db: Session, entry: LeaderboardEntry) -> None:
    db.add(
        LeaderboardRow(
            name=entry.name,
            score=entry.score,
            total=entry.total,
            time_used_seconds=entry.timeUsedSeconds,
            badge=entry.badge,
            math_type=entry.mathType.value if entry.mathType else None,
            difficulty=entry.difficulty.value if entry.difficulty else None,
            grade=entry.grade.value if entry.grade else None,
            achieved_at=entry.achievedAt,
        )
    )
    db.commit()


def query_leaderboard(
    db: Session,
    *,
    math_type: Optional[MathType] = None,
    difficulty: Optional[Difficulty] = None,
    grade: Optional[Grade] = None,
    limit: int = 10,
) -> list[LeaderboardEntry]:
    stmt = select(LeaderboardRow)
    if math_type is not None:
        stmt = stmt.where(LeaderboardRow.math_type == math_type.value)
    if difficulty is not None:
        stmt = stmt.where(LeaderboardRow.difficulty == difficulty.value)
    if grade is not None:
        stmt = stmt.where(LeaderboardRow.grade == grade.value)
    stmt = stmt.order_by(LeaderboardRow.score.desc(), LeaderboardRow.time_used_seconds.asc()).limit(
        limit
    )
    rows = db.scalars(stmt).all()
    return [
        LeaderboardEntry(
            name=r.name,
            score=r.score,
            total=r.total,
            timeUsedSeconds=r.time_used_seconds,
            time=format_time(r.time_used_seconds),
            badge=r.badge,
            mathType=MathType(r.math_type) if r.math_type else None,
            difficulty=Difficulty(r.difficulty) if r.difficulty else None,
            grade=Grade(r.grade) if r.grade else None,
            achievedAt=r.achieved_at,
        )
        for r in rows
    ]


def reset(db: Session) -> None:
    """Wipe all data. Used by tests."""
    db.query(QuizResultRow).delete()
    db.query(QuizRow).delete()
    db.query(LeaderboardRow).delete()
    db.query(UserRow).delete()
    db.commit()
