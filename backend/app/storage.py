"""Database-backed repository. Same interface the routers used for the
previous in-memory store, but now talks to SQLAlchemy."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .db_models import LeaderboardRow, QuizResultRow, QuizRow, UserRow
from .leveling import next_level
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


def create_user(
    db: Session, username: str, pin: str | None = None, recovery_code: str | None = None
) -> User:
    row = UserRow(
        username=username,
        username_lower=username.lower(),
        pin_hash=hash_pin(pin) if pin else None,
        recovery_hash=hash_pin(_normalize_code(recovery_code)) if recovery_code else None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return User(username=row.username, createdAt=row.created_at)


# ---------- rescue codes & brute-force lockout ----------

# Kid-friendly one-time code shown at signup, e.g. "gold-otter-731".
# 16 colors x 32 animals x 1000 numbers ≈ 512k combos; combined with the
# failed-attempt lockout below, guessing is impractical.
_CODE_COLORS = [
    "red", "blue", "green", "gold", "pink", "teal", "plum", "mint",
    "ruby", "jade", "coral", "amber", "ivory", "olive", "navy", "lime",
]
_CODE_ANIMALS = [
    "tiger", "panda", "otter", "eagle", "fox", "bear", "wolf", "koala",
    "zebra", "whale", "shark", "bunny", "gecko", "moose", "llama", "dino",
    "robin", "crab", "seal", "puma", "lynx", "toad", "swan", "ibis",
    "mole", "newt", "orca", "kiwi", "yak", "emu", "bat", "elk",
]

MAX_FAILED_ATTEMPTS = 5
LOCKOUT_MINUTES = 15


def generate_recovery_code() -> str:
    return (
        f"{secrets.choice(_CODE_COLORS)}-{secrets.choice(_CODE_ANIMALS)}"
        f"-{secrets.randbelow(1000):03d}"
    )


def _normalize_code(code: str) -> str:
    return code.strip().lower()


class AccountLockedError(Exception):
    """Too many failed login/reset attempts; retry after the given seconds."""

    def __init__(self, retry_after_seconds: int):
        self.retry_after_seconds = max(1, retry_after_seconds)
        super().__init__(f"locked for {self.retry_after_seconds}s")


def _check_lockout(db: Session, row: UserRow) -> None:
    """Raise if the account is locked; clear an expired lock."""
    if row.locked_until is None:
        return
    now = datetime.now(timezone.utc)
    if now < row.locked_until:
        raise AccountLockedError(int((row.locked_until - now).total_seconds()))
    row.locked_until = None
    row.failed_attempts = 0
    db.commit()


def _register_failure(db: Session, row: UserRow) -> None:
    row.failed_attempts = (row.failed_attempts or 0) + 1
    if row.failed_attempts >= MAX_FAILED_ATTEMPTS:
        row.locked_until = datetime.now(timezone.utc) + timedelta(minutes=LOCKOUT_MINUTES)
    db.commit()


def _clear_failures(db: Session, row: UserRow) -> None:
    if row.failed_attempts or row.locked_until:
        row.failed_attempts = 0
        row.locked_until = None
        db.commit()


def check_login(db: Session, username: str, pin: str) -> Optional[User]:
    """Verify a login. Raises AccountLockedError while locked out."""
    row = get_user_row(db, username)
    if row is None:
        return None
    _check_lockout(db, row)
    if not verify_pin(pin, row.pin_hash):
        _register_failure(db, row)
        return None
    _clear_failures(db, row)
    return User(username=row.username, createdAt=row.created_at)


def reset_pin(db: Session, username: str, recovery_code: str, new_pin: str) -> Optional[User]:
    """Set a new PIN if the rescue code matches.

    Counts toward the same lockout as logins, so the rescue code can't be
    brute-forced either. Raises AccountLockedError while locked out.
    """
    row = get_user_row(db, username)
    if row is None:
        return None
    _check_lockout(db, row)
    if not verify_pin(_normalize_code(recovery_code), row.recovery_hash):
        _register_failure(db, row)
        return None
    row.pin_hash = hash_pin(new_pin)
    _clear_failures(db, row)
    db.commit()
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


def suggest_level(db: Session, username: str) -> Optional[SuggestedLevel]:
    """Recommend a starting level from recent history.

    Averages the player's recent quizzes at their latest level and steps
    through the shared ladder (app.leveling.next_level) — the same
    up/down logic the end-of-quiz recommendation uses, so the two never
    disagree. Returns None when there's nothing to go on.
    """
    rows = [r for r in _user_entries(db, username) if r.grade and r.difficulty]
    if not rows:
        return None

    latest = rows[0]
    # Average across the recent runs that share the latest level.
    same_level = [
        r for r in rows[:10] if r.grade == latest.grade and r.difficulty == latest.difficulty
    ]
    avg = sum(r.score for r in same_level) / len(same_level)

    grade, difficulty, _ = next_level(Grade(latest.grade), Difficulty(latest.difficulty), avg)
    return SuggestedLevel(grade=grade, difficulty=difficulty, basedOn=len(same_level))


def reset(db: Session) -> None:
    """Wipe all data. Used by tests."""
    db.query(QuizResultRow).delete()
    db.query(QuizRow).delete()
    db.query(LeaderboardRow).delete()
    db.query(UserRow).delete()
    db.commit()
