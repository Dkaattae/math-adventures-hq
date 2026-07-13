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


class Difficulty(str, Enum):
    easy = "easy"
    medium = "medium"
    hard = "hard"


# ---------- users ----------

class User(BaseModel):
    username: str
    createdAt: datetime


class UserCreate(BaseModel):
    username: str = Field(min_length=1, max_length=20)


class UsernameAvailability(BaseModel):
    username: str
    available: bool


# ---------- quizzes ----------

class Question(BaseModel):
    id: int = Field(ge=0)
    question: str


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


class QuizCreate(BaseModel):
    username: str
    grade: Grade
    mathType: MathType
    difficulty: Difficulty


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


class QuizResult(BaseModel):
    quizId: UUID
    username: str
    score: int = Field(ge=0, le=10)
    total: int = 10
    timeUsedSeconds: int
    badge: Optional[str] = None
    results: list[QuestionResult]
    submittedAt: datetime


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


# ---------- errors ----------

class ErrorResponse(BaseModel):
    code: str
    message: str
    details: Optional[dict] = None
