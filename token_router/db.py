"""SQLite user database with async support."""

from __future__ import annotations

import logging
import secrets
import sqlite3
import time
import uuid

from token_router.config import settings

logger = logging.getLogger(__name__)

_conn: sqlite3.Connection | None = None

CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS users (
    id            TEXT PRIMARY KEY,
    email         TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    display_name  TEXT DEFAULT '',
    created_at    REAL NOT NULL,
    is_active     INTEGER DEFAULT 1,
    api_key       TEXT UNIQUE NOT NULL
);
"""


def _generate_api_key() -> str:
    return "tr-" + secrets.token_hex(24)


def init_db() -> None:
    """Initialize database and create tables."""
    global _conn
    _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute(CREATE_TABLE)
    _conn.commit()
    logger.info("User DB initialized: %s", settings.db_path)


def close_db() -> None:
    global _conn
    if _conn:
        _conn.close()
        _conn = None


def _get_conn() -> sqlite3.Connection:
    if _conn is None:
        init_db()
    return _conn  # type: ignore[return-value]


def create_user(email: str, password_hash: str, display_name: str = "") -> dict:
    """Create a new user. Returns user dict."""
    conn = _get_conn()
    user_id = str(uuid.uuid4())
    api_key = _generate_api_key()
    now = time.time()
    conn.execute(
        "INSERT INTO users (id, email, password_hash, display_name, created_at, api_key) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, email, password_hash, display_name, now, api_key),
    )
    conn.commit()
    return {"id": user_id, "email": email, "display_name": display_name, "api_key": api_key, "created_at": now}


def get_user_by_email(email: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ? AND is_active = 1", (email,)).fetchone()
    return dict(row) if row else None


def get_user_by_id(user_id: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ? AND is_active = 1", (user_id,)).fetchone()
    return dict(row) if row else None


def get_user_by_api_key(api_key: str) -> dict | None:
    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE api_key = ? AND is_active = 1", (api_key,)).fetchone()
    return dict(row) if row else None
