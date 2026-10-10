from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    ForeignKey,
)
from sqlalchemy.sql import func
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    email = Column(
        String(255),
        unique=True,
        index=True,
        nullable=False,
    )
    hashed_password = Column(String(255), nullable=False)


class Attempt(Base):
    """Stores individual quiz answers."""

    __tablename__ = "attempts"

    id = Column(Integer, primary_key=True, index=True)
    topic = Column(String, nullable=False)
    difficulty = Column(String, nullable=False)
    is_correct = Column(Boolean, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
    )

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True,
        index=True,
    )


class QuizResult(Base):
    """Stores the final result of each completed quiz."""

    __tablename__ = "quiz_results"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False,
        index=True,
    )

    subject = Column(String(100), nullable=False)
    topic = Column(String(150), nullable=False)
    difficulty = Column(String(30), nullable=False)

    total_questions = Column(Integer, nullable=False)
    correct_answers = Column(Integer, nullable=False)
    score_percentage = Column(Integer, nullable=False)

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )