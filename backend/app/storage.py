"""Database-backed repository. Same interface the routers used for the
previous in-memory store, but now talks to SQLAlchemy."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
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
    RecentQuiz,
    SuggestedLevel,
    TopicStat,
    User,
    UserStats,
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
        "options": q.options,
        "figure": q.figure,
    }


def _question_from_json(d: dict) -> QuestionInternal:
    return QuestionInternal(**d)


def _result_item_to_json(r: QuestionResult) -> dict:
    return r.model_dump()


# ---------- users ----------

def hash_pin(pin: str, salt: str | None = None) -> str:
    """PBKDF2 hash as 'salt$hexhash'. Stdlib only — no new dependency."""
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", pin.encode(), bytes.fromhex(salt), 100_000).hex()
    return f"{salt}${digest}"


def verify_pin(pin: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    return secrets.compare_digest(hash_pin(pin, salt), stored)


def user_exists(db: Session, username: str) -> bool:
    return db.scalar(select(UserRow).where(UserRow.username_lower == username.lower())) is not None


def get_user_row(db: Session, username: str) -> Optional[UserRow]:
    return db.scalar(select(UserRow).where(UserRow.username_lower == username.lower()))


def create_user(db: Session, username: str, pin: str | None = None) -> User:
    row = UserRow(
        username=username,
        username_lower=username.lower(),
        pin_hash=hash_pin(pin) if pin else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return User(username=row.username, createdAt=row.created_at)


def check_login(db: Session, username: str, pin: str) -> Optional[User]:
    row = get_user_row(db, username)
    if row is None or not verify_pin(pin, row.pin_hash):
        return None
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


# ---------- per-user progress ----------

def _user_entries(db: Session, username: str) -> list[LeaderboardRow]:
    """All of a player's submitted quizzes, newest first."""
    stmt = (
        select(LeaderboardRow)
        .where(func.lower(LeaderboardRow.name) == username.lower())
        .order_by(LeaderboardRow.achieved_at.desc())
    )
    return list(db.scalars(stmt).all())


def query_user_stats(db: Session, username: str) -> UserStats:
    rows = _user_entries(db, username)
    if not rows:
        return UserStats(
            username=username, totalQuizzes=0, averageScore=0.0,
            bestScore=0, byTopic=[], recent=[],
        )

    scores = [r.score for r in rows]
    by_topic: dict[str, list[int]] = {}
    for r in rows:
        if r.math_type:
            by_topic.setdefault(r.math_type, []).append(r.score)

    topic_stats = [
        TopicStat(
            mathType=MathType(mt),
            quizzes=len(s),
            averageScore=round(sum(s) / len(s), 1),
            bestScore=max(s),
        )
        for mt, s in sorted(by_topic.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]

    recent = [
        RecentQuiz(
            mathType=MathType(r.math_type) if r.math_type else None,
            grade=Grade(r.grade) if r.grade else None,
            difficulty=Difficulty(r.difficulty) if r.difficulty else None,
            score=r.score,
            total=r.total,
            time=format_time(r.time_used_seconds),
            achievedAt=r.achieved_at,
        )
        for r in rows[:5]
    ]

    return UserStats(
        username=username,
        totalQuizzes=len(rows),
        averageScore=round(sum(scores) / len(scores), 1),
        bestScore=max(scores),
        byTopic=topic_stats,
        recent=recent,
    )


_GRADE_LADDER = [Grade.K, Grade.G1, Grade.G2, Grade.G3, Grade.G4, Grade.G5]
_DIFF_LADDER = [Difficulty.easy, Difficulty.medium, Difficulty.hard]


def suggest_level(db: Session, username: str) -> Optional[SuggestedLevel]:
    """Recommend a starting level from recent history.

    Looks at the player's most recent quizzes at their latest level and
    nudges up (avg >= 9), down (avg <= 4), or holds — the history-based
    counterpart to the end-of-quiz recommendation on the results screen.
    Returns None when there's nothing to go on.
    """
    rows = [r for r in _user_entries(db, username) if r.grade and r.difficulty]
    if not rows:
        return None

    latest = rows[0]
    grade, difficulty = Grade(latest.grade), Difficulty(latest.difficulty)

    # Average across the recent runs that share the latest level.
    same_level = [
        r for r in rows[:10] if r.grade == latest.grade and r.difficulty == latest.difficulty
    ]
    avg = sum(r.score for r in same_level) / len(same_level)

    gi, di = _GRADE_LADDER.index(grade), _DIFF_LADDER.index(difficulty)
    if avg >= 9:
        if di < len(_DIFF_LADDER) - 1:
            difficulty = _DIFF_LADDER[di + 1]
        elif gi < len(_GRADE_LADDER) - 1:
            grade, difficulty = _GRADE_LADDER[gi + 1], Difficulty.easy
    elif avg <= 4:
        if di > 0:
            difficulty = _DIFF_LADDER[di - 1]
        elif gi > 0:
            grade, difficulty = _GRADE_LADDER[gi - 1], Difficulty.hard

    return SuggestedLevel(grade=grade, difficulty=difficulty, basedOn=len(same_level))


def reset(db: Session) -> None:
    """Wipe all data. Used by tests."""
    db.query(QuizResultRow).delete()
    db.query(QuizRow).delete()
    db.query(LeaderboardRow).delete()
    db.query(UserRow).delete()
    db.commit()
