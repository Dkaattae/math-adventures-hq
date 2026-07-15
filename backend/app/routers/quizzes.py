from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import storage
from ..db import get_session
from ..models import (
    ErrorResponse,
    Difficulty,
    Grade,
    LeaderboardEntry,
    MathType,
    Question,
    QuestionResult,
    Quiz,
    QuizCreate,
    QuizResult,
    QuizSubmit,
)
from ..questions import generate_questions, grade_answer

router = APIRouter(prefix="/api/quizzes", tags=["quizzes"])


def _badge_for(score: int) -> str | None:
    if score == 10:
        return "🏆"
    if score >= 8:
        return "🥈"
    if score >= 6:
        return "🥉"
    if score >= 4:
        return "⭐"
    return None


def _public_questions(internal_qs) -> list[Question]:
    return [
        Question(id=q.id, question=q.question, options=q.options, figure=q.figure)
        for q in internal_qs
    ]


@router.post("", response_model=Quiz, status_code=201)
def create_quiz(payload: QuizCreate, db: Session = Depends(get_session)) -> Quiz:
    if not storage.user_exists(db, payload.username):
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(
                code="user_not_found",
                message=f"Unknown user '{payload.username}'.",
            ).model_dump(),
        )
    quiz_id = uuid4()
    internal_qs = generate_questions(
        payload.mathType, payload.difficulty, payload.grade, answer_mode=payload.answerMode
    )
    row = storage.save_quiz(
        db, quiz_id, payload.username, payload.grade, payload.mathType, payload.difficulty, internal_qs
    )
    return Quiz(
        id=quiz_id,
        username=payload.username,
        grade=payload.grade,
        mathType=payload.mathType,
        difficulty=payload.difficulty,
        questions=_public_questions(internal_qs),
        createdAt=row.created_at,
    )


@router.get("/{quiz_id}", response_model=Quiz)
def get_quiz(quiz_id: UUID, db: Session = Depends(get_session)) -> Quiz:
    row = storage.get_quiz(db, quiz_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(code="quiz_not_found", message="Quiz not found.").model_dump(),
        )
    return Quiz(
        id=row.id,
        username=row.username,
        grade=Grade(row.grade),
        mathType=MathType(row.math_type),
        difficulty=Difficulty(row.difficulty),
        questions=_public_questions(storage.quiz_questions(row)),
        createdAt=row.created_at,
    )


@router.post("/{quiz_id}/submit", response_model=QuizResult)
def submit_quiz(
    quiz_id: UUID, payload: QuizSubmit, db: Session = Depends(get_session)
) -> QuizResult:
    row = storage.get_quiz(db, quiz_id)
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorResponse(code="quiz_not_found", message="Quiz not found.").model_dump(),
        )
    if row.submitted:
        raise HTTPException(
            status_code=409,
            detail=ErrorResponse(
                code="already_submitted", message="Quiz has already been submitted."
            ).model_dump(),
        )

    internal_qs = storage.quiz_questions(row)
    results: list[QuestionResult] = []
    score = 0
    for q, user_ans in zip(internal_qs, payload.answers):
        is_correct = grade_answer(q.correctAnswer, user_ans)
        if is_correct:
            score += 1
        results.append(
            QuestionResult(
                id=q.id,
                question=q.question,
                correctAnswer=q.correctAnswer,
                explanation=q.explanation,
                userAnswer=user_ans,
                isCorrect=is_correct,
                figure=q.figure,
            )
        )

    submitted_at = datetime.now(timezone.utc)
    # timeUsedSeconds is client-reported and feeds the leaderboard's
    # tie-breaker, so cap it at the window the server actually observed
    # between quiz creation and submission (rounded up a second to not
    # penalize honest sub-second clock skew).
    server_elapsed = max(0, int((submitted_at - row.created_at).total_seconds()) + 1)
    time_used = min(payload.timeUsedSeconds, server_elapsed)
    result = QuizResult(
        quizId=quiz_id,
        username=row.username,
        score=score,
        total=10,
        timeUsedSeconds=time_used,
        badge=_badge_for(score),
        results=results,
        submittedAt=submitted_at,
    )
    storage.mark_submitted(db, quiz_id, result)
    storage.add_leaderboard_entry(
        db,
        LeaderboardEntry(
            name=row.username,
            score=score,
            total=10,
            timeUsedSeconds=time_used,
            time=storage.format_time(time_used),
            badge=_badge_for(score),
            mathType=MathType(row.math_type),
            difficulty=Difficulty(row.difficulty),
            grade=Grade(row.grade),
            achievedAt=submitted_at,
        ),
    )
    return result
