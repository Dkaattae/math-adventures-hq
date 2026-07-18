"""SQLAlchemy ORM models."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import CHAR, TypeDecorator

from .db import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """Timezone-aware UTC datetimes on every backend.

    Postgres honors DateTime(timezone=True) and returns aware values, but
    sqlite silently drops the tzinfo and returns naive ones. Store
    everything as UTC and re-attach the UTC tzinfo on read so callers can
    do aware datetime arithmetic regardless of the backend.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None and value.tzinfo is not None:
            return value.astimezone(timezone.utc)
        return value

    def process_result_value(self, value, dialect):
        if value is not None and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value


class GUID(TypeDecorator):
    """Portable UUID — uses native UUID on Postgres, CHAR(36) elsewhere."""

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == "postgresql":
            from sqlalchemy.dialects.postgresql import UUID as PG_UUID

            return dialect.type_descriptor(PG_UUID(as_uuid=True))
        return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if dialect.name == "postgresql":
            return value if isinstance(value, UUID) else UUID(str(value))
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return value if isinstance(value, UUID) else UUID(str(value))


class UserRow(Base):
    __tablename__ = "users"
    username: Mapped[str] = mapped_column(String(20), primary_key=True)
    username_lower: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    # PBKDF2 "salt$hash" of the player's 4-digit PIN. Nullable for rows
    # created before PINs existed (those simply can't log back in).
    pin_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # PBKDF2 hash of the one-time "rescue code" shown at signup, used to
    # reset a forgotten PIN. Same nullable story as pin_hash.
    recovery_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Brute-force lockout: consecutive failed login/reset attempts, and
    # the moment the account unlocks again (null = not locked).
    failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)


class QuizRow(Base):
    __tablename__ = "quizzes"
    id: Mapped[UUID] = mapped_column(GUID(), primary_key=True, default=uuid4)
    username: Mapped[str] = mapped_column(String(20), ForeignKey("users.username"))
    grade: Mapped[str] = mapped_column(String(2))
    math_type: Mapped[str] = mapped_column(String(20))
    difficulty: Mapped[str] = mapped_column(String(10))
    # Stores full questions incl. correct answer + explanation.
    questions_json: Mapped[list] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
    submitted: Mapped[bool] = mapped_column(Boolean, default=False)

    result: Mapped["QuizResultRow | None"] = relationship(
        back_populates="quiz", uselist=False, cascade="all, delete-orphan"
    )


class QuizResultRow(Base):
    __tablename__ = "quiz_results"
    quiz_id: Mapped[UUID] = mapped_column(GUID(), ForeignKey("quizzes.id"), primary_key=True)
    username: Mapped[str] = mapped_column(String(20))
    score: Mapped[int] = mapped_column(Integer)
    total: Mapped[int] = mapped_column(Integer, default=10)
    time_used_seconds: Mapped[int] = mapped_column(Integer)
    badge: Mapped[str | None] = mapped_column(String(8), nullable=True)
    results_json: Mapped[list] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)

    quiz: Mapped[QuizRow] = relationship(back_populates="result")


class LeaderboardRow(Base):
    __tablename__ = "leaderboard"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(20), index=True)
    score: Mapped[int] = mapped_column(Integer, index=True)
    total: Mapped[int] = mapped_column(Integer, default=10)
    time_used_seconds: Mapped[int] = mapped_column(Integer)
    badge: Mapped[str | None] = mapped_column(String(8), nullable=True)
    math_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    difficulty: Mapped[str | None] = mapped_column(String(10), nullable=True, index=True)
    grade: Mapped[str | None] = mapped_column(String(2), nullable=True, index=True)
    achieved_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=_utcnow)
