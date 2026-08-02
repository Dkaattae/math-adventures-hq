"""Pydantic schemas matching openapi.yaml."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Annotated, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints


# ---------- enums ----------

class Grade(str, Enum):
    K = "K"
    G1 = "1"
    G2 = "2"
    G3 = "3"
    G4 = "4"
    G5 = "5"


class MathType(str, Enum):
    addition = "addition"
    subtraction = "subtraction"
    multiplication = "multiplication"
    division = "division"
    algebra = "algebra"
    geometry = "geometry"
    fractions = "fractions"
    order_of_operations = "order_of_operations"
    word_problems = "word_problems"
    comparison = "comparison"
    money_time = "money_time"
    decimals = "decimals"
    percentages = "percentages"
    measurement = "measurement"
    mixed = "mixed"


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


class AnswerMode(str, Enum):
    typing = "typing"
    multiple_choice = "multiple_choice"


class AnswerKind(str, Enum):
    """Shape of a question's answer, so the client can pick a keyboard."""
    integer = "integer"    # non-negative whole number → numeric keypad
    decimal = "decimal"    # non-negative decimal → keypad with a "."
    text = "text"          # fractions, "<", words, negatives → full keyboard


# ---------- users ----------

# Usernames are a shared, unauthenticated namespace, so keep the charset
# boring: a letter/digit first, then letters, digits, spaces, hyphens,
# underscores or apostrophes ("Anna-Lee", "O'Neil", "kid_7" all pass).
# \w is Unicode-aware, so non-English names work; control characters,
# markup and emoji do not.
USERNAME_PATTERN = r"^[^\W_][\w \-']*$"

Username = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True, min_length=1, max_length=20, pattern=USERNAME_PATTERN
    ),
]


class User(BaseModel):
    username: str
    createdAt: datetime


class AuthenticatedUser(User):
    """Signup/login response: carries the session token for /stats etc."""
    token: str


class UserCreated(AuthenticatedUser):
    """Signup response: includes the one-time rescue code (never shown again)."""
    recoveryCode: str


class UserCreate(BaseModel):
    username: Username
    pin: str = Field(pattern=r"^\d{4}$", description="4-digit numeric PIN")


class UserLogin(BaseModel):
    username: Username
    pin: str = Field(pattern=r"^\d{4}$")


class PinReset(BaseModel):
    username: Username
    recoveryCode: str = Field(min_length=1, max_length=40)
    newPin: str = Field(pattern=r"^\d{4}$")


class UsernameAvailability(BaseModel):
    username: str
    available: bool


# ---------- quizzes ----------

class Question(BaseModel):
    id: int = Field(ge=0)
    question: str
    # Present only for multiple-choice quizzes: the shuffled answer
    # choices (one of which is correct). None means "type your answer".
    options: Optional[list[str]] = None
    # Present for visual geometry: a shape name the client draws as SVG
    # (e.g. "pentagon", "circle"). None for non-visual questions.
    figure: Optional[str] = None
    # What sort of answer to expect, so phones can show the right
    # keyboard for typed answers. Ignored in multiple-choice mode.
    answerKind: AnswerKind = AnswerKind.text
    # Seconds this question is worth on the clock. Long word-problem
    # scenes need reading time that a one-line sum doesn't.
    timeLimitSeconds: int = Field(default=15, ge=5, le=300)


class QuestionInternal(Question):
    """Question plus correct answer / explanation — never returned on GET /quizzes."""
    correctAnswer: Union[int, str]
    explanation: str
    # Which topic actually produced this question. Equal to the quiz's
    # topic except in a 🎲 Mixed quiz, where every question comes from a
    # different one — and a word problem needs its own clock whichever
    # quiz it turns up in. None on quizzes stored before this existed.
    topic: Optional[MathType] = None


class QuestionResult(BaseModel):
    id: int
    question: str
    correctAnswer: Union[int, str]
    explanation: str
    userAnswer: Optional[str]
    isCorrect: bool
    figure: Optional[str] = None


class QuizCreate(BaseModel):
    username: Username
    grade: Grade
    mathType: MathType
    difficulty: Difficulty
    answerMode: AnswerMode = AnswerMode.typing


class Quiz(BaseModel):
    id: UUID
    username: str
    grade: Grade
    mathType: MathType
    difficulty: Difficulty
    questions: list[Question]
    createdAt: datetime


class QuizSubmit(BaseModel):
    answers: list[Optional[str]] = Field(min_length=10, max_length=10)
    timeUsedSeconds: int = Field(ge=0)


class Recommendation(BaseModel):
    """What to play next, from the shared level ladder (app/leveling.py)."""
    direction: str  # "up" | "steady" | "down"
    grade: Grade
    difficulty: Difficulty


class QuizResult(BaseModel):
    quizId: UUID
    username: str
    score: int = Field(ge=0, le=10)
    total: int = 10
    timeUsedSeconds: int
    badge: Optional[str] = None
    results: list[QuestionResult]
    submittedAt: datetime
    recommendation: Optional[Recommendation] = None


# ---------- leaderboard ----------

class LeaderboardEntry(BaseModel):
    name: str
    score: int
    total: int
    timeUsedSeconds: int
    time: str
    badge: Optional[str] = None
    mathType: Optional[MathType] = None
    difficulty: Optional[Difficulty] = None
    grade: Optional[Grade] = None
    achievedAt: datetime


# ---------- progress / stats ----------

class TopicStat(BaseModel):
    mathType: MathType
    quizzes: int
    averageScore: float
    bestScore: int


class RecentQuiz(BaseModel):
    mathType: Optional[MathType] = None
    grade: Optional[Grade] = None
    difficulty: Optional[Difficulty] = None
    score: int
    total: int
    time: str
    achievedAt: datetime


class UserStats(BaseModel):
    username: str
    totalQuizzes: int
    averageScore: float
    bestScore: int
    byTopic: list[TopicStat]
    recent: list[RecentQuiz]


class SuggestedLevel(BaseModel):
    """Next level to start a returning player at, from their history."""
    grade: Grade
    difficulty: Difficulty
    basedOn: int  # recent quizzes that informed the suggestion (0 = new topic)
    # Topic the suggestion was computed for; None = overall history.
    mathType: Optional[MathType] = None


# ---------- errors ----------

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
