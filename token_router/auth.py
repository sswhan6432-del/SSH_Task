"""JWT authentication utilities."""

from __future__ import annotations

import time
from typing import Optional

import jwt
from fastapi import Depends, HTTPException, Request

from token_router.config import settings

ALGORITHM = "HS256"


def create_token(user_id: str, email: str) -> str:
    """Create a JWT access token."""
    now = time.time()
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + settings.jwt_expiry_hours * 3600,
        "type": "access",
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_token(token: str) -> dict | None:
    """Decode and validate a JWT. Returns payload or None."""
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[ALGORITHM])
    except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
        return None


def get_current_user_id(request: Request) -> str:
    """FastAPI dependency - extract user_id from request.state (set by middleware)."""
    user_id = getattr(request.state, "user_id", None)
    if not user_id:
        raise HTTPException(status_code=401, detail={"error": {"message": "Authentication required", "type": "authentication_error"}})
    return user_id


def get_optional_user_id(request: Request) -> str:
    """FastAPI dependency - returns user_id or '__anonymous__'."""
    return getattr(request.state, "user_id", "__anonymous__")
