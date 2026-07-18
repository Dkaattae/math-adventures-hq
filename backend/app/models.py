"""Pydantic schemas matching openapi.yaml."""
from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field


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


# ---------- users ----------

class User(BaseModel):
    username: str
    createdAt: datetime


class UserCreated(User):
    """Signup response: includes the one-time rescue code (never shown again)."""
    recoveryCode: str


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    pin: str = Field(pattern=r"^\d{4}$", description="4-digit numeric PIN")


class UserLogin(BaseModel):
    username: str = Field(min_length=1, max_length=20)
    pin: str = Field(pattern=r"^\d{4}$")


class PinReset(BaseModel):
    username: str = Field(min_length=1, max_length=20)
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


class QuestionInternal(Question):
    """Question plus correct answer / explanation — never returned on GET /quizzes."""
    correctAnswer: Union[int, str]
    explanation: str


class QuestionResult(BaseModel):
    id: int
    question: str
    correctAnswer: Union[int, str]
    explanation: str
    userAnswer: Optional[str]
    isCorrect: bool
    figure: Optional[str] = None


class QuizCreate(BaseModel):
    username: str
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
