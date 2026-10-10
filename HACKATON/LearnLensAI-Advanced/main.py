
import os
from pathlib import Path
from datetime import datetime

from fastapi import FastAPI, Depends, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database import Base, engine, get_db
from app.models import User, Attempt, QuizResult
from app.routers import auth


# --------------------------------------------------
# PATHS AND APPLICATION SETUP
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

# Your actual frontend is inside app/static/
STATIC_DIR = BASE_DIR / "app" / "static"
INDEX_FILE = STATIC_DIR / "index.html"

app = FastAPI(title="LearnLens AI API")

SECRET_KEY = os.getenv("LEARNLENS_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "LEARNLENS_SECRET_KEY is missing. "
        "Set it in your environment before starting the server."
    )

ALGORITHM = "HS256"

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

# Create database tables.
Base.metadata.create_all(bind=engine)

# IMPORTANT:
# main.py supplies the /api/auth prefix.
# auth.py must use APIRouter(tags=["Authentication"])
# without another /api/auth prefix.
app.include_router(
    auth.router,
    prefix="/api/auth",
    tags=["Authentication"],
)


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class QuizResultCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=100)
    topic: str = Field(min_length=1, max_length=150)
    difficulty: str = Field(min_length=1, max_length=30)
    total_questions: int = Field(gt=0, le=500)
    correct_answers: int = Field(ge=0, le=500)


class AnswerAttemptCreate(BaseModel):
    topic: str = Field(min_length=1, max_length=150)
    difficulty: str = Field(min_length=1, max_length=30)
    is_correct: bool


# --------------------------------------------------
# AUTHENTICATED USER
# --------------------------------------------------

def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
        )

        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=401,
                detail="Invalid login token",
            )

        user_id = int(user_id)

    except (JWTError, ValueError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired login token",
        )

    user = db.query(User).filter(
        User.id == user_id
    ).first()

    if user is None:
        raise HTTPException(
            status_code=401,
            detail="Account not found",
        )

    return user


# --------------------------------------------------
# SAVE COMPLETED QUIZ
# --------------------------------------------------

@app.post("/api/quiz-results", status_code=201)
def save_quiz_result(
    data: QuizResultCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if data.correct_answers > data.total_questions:
        raise HTTPException(
            status_code=400,
            detail="Correct answers cannot exceed total questions",
        )

    percentage = round(
        data.correct_answers / data.total_questions * 100
    )

    result = QuizResult(
        user_id=user.id,
        subject=data.subject,
        topic=data.topic,
        difficulty=data.difficulty,
        total_questions=data.total_questions,
        correct_answers=data.correct_answers,
        score_percentage=percentage,
    )

    db.add(result)
    db.commit()
    db.refresh(result)

    return {
        "message": "Quiz result saved successfully",
        "id": result.id,
        "subject": result.subject,
        "topic": result.topic,
        "difficulty": result.difficulty,
        "total_questions": result.total_questions,
        "correct_answers": result.correct_answers,
        "score_percentage": result.score_percentage,
        "created_at": result.created_at,
    }


# --------------------------------------------------
# GET QUIZ HISTORY
# --------------------------------------------------

@app.get("/api/quiz-results")
def get_quiz_results(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = (
        db.query(QuizResult)
        .filter(QuizResult.user_id == user.id)
        .order_by(QuizResult.created_at.desc())
        .all()
    )

    return [
        {
            "id": result.id,
            "subject": result.subject,
            "topic": result.topic,
            "difficulty": result.difficulty,
            "total_questions": result.total_questions,
            "correct_answers": result.correct_answers,
            "score_percentage": result.score_percentage,
            "created_at": result.created_at,
        }
        for result in results
    ]


# --------------------------------------------------
# DASHBOARD STATISTICS
# --------------------------------------------------

@app.get("/api/quiz-stats")
def get_quiz_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    results = (
        db.query(QuizResult)
        .filter(QuizResult.user_id == user.id)
        .all()
    )

    total_questions = sum(
        result.total_questions for result in results
    )
    total_correct = sum(
        result.correct_answers for result in results
    )

    accuracy = (
        round(total_correct / total_questions * 100)
        if total_questions else 0
    )

    return {
        "quiz_attempts": len(results),
        "total_questions": total_questions,
        "total_correct": total_correct,
        "accuracy": accuracy,
        "results": [
            {
                "id": result.id,
                "subject": result.subject,
                "topic": result.topic,
                "score": (
                    f"{result.correct_answers}/"
                    f"{result.total_questions}"
                ),
                "percentage": result.score_percentage,
                "created_at": result.created_at,
            }
            for result in sorted(
                results,
                key=lambda item: item.created_at or datetime.min,
                reverse=True,
            )
        ],
    }


# --------------------------------------------------
# INDIVIDUAL ANSWER ATTEMPTS
# --------------------------------------------------

@app.post("/api/attempts", status_code=201)
def save_answer_attempt(
    data: AnswerAttemptCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempt = Attempt(
        topic=data.topic,
        difficulty=data.difficulty,
        is_correct=data.is_correct,
        user_id=user.id,
    )

    db.add(attempt)
    db.commit()
    db.refresh(attempt)

    return {
        "id": attempt.id,
        "topic": attempt.topic,
        "difficulty": attempt.difficulty,
        "is_correct": attempt.is_correct,
        "created_at": attempt.created_at,
    }


@app.get("/api/attempts")
def get_answer_attempts(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    attempts = (
        db.query(Attempt)
        .filter(Attempt.user_id == user.id)
        .order_by(Attempt.created_at.desc())
        .all()
    )

    return [
        {
            "id": attempt.id,
            "topic": attempt.topic,
            "difficulty": attempt.difficulty,
            "is_correct": attempt.is_correct,
            "created_at": attempt.created_at,
        }
        for attempt in attempts
    ]


# --------------------------------------------------
# FRONTEND
# --------------------------------------------------

@app.get("/", include_in_schema=False)
def home():
    if not INDEX_FILE.is_file():
        raise HTTPException(
            status_code=500,
            detail=f"Frontend file not found: {INDEX_FILE}",
        )

    return FileResponse(INDEX_FILE)


# Serve frontend assets from app/static/
app.mount(
    "/static",
    StaticFiles(directory=STATIC_DIR),
    name="static",
)
