"""POST /v1/auth/signup, /v1/auth/login, GET /v1/auth/me - Authentication endpoints."""

from __future__ import annotations

import logging
import re

import bcrypt as _bcrypt
from fastapi import APIRouter, Depends, HTTPException

from token_router import db
from token_router.auth import create_token, get_current_user_id
from token_router.models import AuthResponse, LoginRequest, SignupRequest, UserProfile


def _hash_password(password: str) -> str:
    return _bcrypt.hashpw(password.encode(), _bcrypt.gensalt()).decode()


def _verify_password(password: str, hashed: str) -> bool:
    return _bcrypt.checkpw(password.encode(), hashed.encode())

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/v1/auth", tags=["Auth"])

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@router.post("/signup", response_model=AuthResponse)
async def signup(req: SignupRequest):
    """Create a new account and return JWT."""
    if not EMAIL_RE.match(req.email):
        raise HTTPException(status_code=400, detail={"error": {"message": "Invalid email format", "type": "validation_error"}})
    if len(req.password) < 8:
        raise HTTPException(status_code=400, detail={"error": {"message": "Password must be at least 8 characters", "type": "validation_error"}})

    existing = db.get_user_by_email(req.email)
    if existing:
        raise HTTPException(status_code=409, detail={"error": {"message": "Email already registered", "type": "conflict_error"}})

    password_hash = _hash_password(req.password)
    user = db.create_user(email=req.email, password_hash=password_hash, display_name=req.display_name or "")
    token = create_token(user["id"], user["email"])

    logger.info("New user registered: %s", user["email"])
    return AuthResponse(token=token, user={"id": user["id"], "email": user["email"], "display_name": user["display_name"], "api_key": user["api_key"]})


@router.post("/login", response_model=AuthResponse)
async def login(req: LoginRequest):
    """Authenticate and return JWT."""
    user = db.get_user_by_email(req.email)
    if not user or not _verify_password(req.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail={"error": {"message": "Invalid email or password", "type": "authentication_error"}})

    token = create_token(user["id"], user["email"])
    logger.info("User logged in: %s", user["email"])
    return AuthResponse(token=token, user={"id": user["id"], "email": user["email"], "display_name": user["display_name"], "api_key": user["api_key"]})


@router.get("/me", response_model=UserProfile)
async def get_me(user_id: str = Depends(get_current_user_id)):
    """Get current user profile."""
    user = db.get_user_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail={"error": {"message": "User not found", "type": "not_found_error"}})

    return UserProfile(
        id=user["id"],
        email=user["email"],
        display_name=user["display_name"],
        api_key=user["api_key"],
        created_at=user["created_at"],
    )
