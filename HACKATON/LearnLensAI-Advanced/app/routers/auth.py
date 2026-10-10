
import os
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User


# --------------------------------------------------
# ROUTER SETUP
# --------------------------------------------------

# Do not add /api/auth here.
# main.py already adds that prefix.
router = APIRouter(tags=["Authentication"])

password_hash = PasswordHash.recommended()

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login"
)

SECRET_KEY = os.getenv("LEARNLENS_SECRET_KEY")

if not SECRET_KEY:
    raise RuntimeError(
        "Set the LEARNLENS_SECRET_KEY environment variable before starting."
    )

ALGORITHM = "HS256"
TOKEN_MINUTES = 60 * 24


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class RegisterRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


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

    except (jwt.PyJWTError, ValueError, TypeError):
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
# REGISTER
# --------------------------------------------------

@router.post("/register", status_code=201)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    name = data.name.strip()
    email = str(data.email).strip().lower()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Name is required",
        )

    existing = db.query(User).filter(
        User.email == email
    ).first()

    if existing:
        raise HTTPException(
            status_code=409,
            detail="Email already registered",
        )

    user = User(
        name=name,
        email=email,
        hashed_password=password_hash.hash(data.password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail="Could not create account. Please try again.",
        )

    return {
        "message": "Account created successfully",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }


# --------------------------------------------------
# LOGIN
# --------------------------------------------------

@router.post("/login")
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    email = str(data.email).strip().lower()

    user = db.query(User).filter(
        User.email == email
    ).first()

    if not user or not password_hash.verify(
        data.password,
        user.hashed_password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
        )

    expires = datetime.now(timezone.utc) + timedelta(
        minutes=TOKEN_MINUTES
    )

    token = jwt.encode(
        {
            "sub": str(user.id),
            "exp": expires,
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return {
        "access_token": token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "name": user.name,
            "email": user.email,
        },
    }


# --------------------------------------------------
# CURRENT USER PROFILE
# --------------------------------------------------

@router.get("/me")
def me(
    user: User = Depends(get_current_user),
):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
    }

