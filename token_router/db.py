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

CREATE_USERS_TABLE = """
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

CREATE_PROVIDER_KEYS_TABLE = """
CREATE TABLE IF NOT EXISTS provider_keys (
    id         TEXT PRIMARY KEY,
    user_id    TEXT NOT NULL REFERENCES users(id),
    provider   TEXT NOT NULL,
    api_key    TEXT NOT NULL,
    label      TEXT DEFAULT '',
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL,
    UNIQUE(user_id, provider)
);
"""


def _generate_api_key() -> str:
    return "tr-" + secrets.token_hex(24)


def init_db() -> None:
    """Initialize database and create tables."""
    global _conn
    _conn = sqlite3.connect(settings.db_path, check_same_thread=False)
    _conn.row_factory = sqlite3.Row
    _conn.execute("PRAGMA foreign_keys = ON")
    _conn.execute(CREATE_USERS_TABLE)
    _conn.execute(CREATE_PROVIDER_KEYS_TABLE)
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


# ── Provider Keys CRUD ─────────────────────────────────────────

def upsert_provider_key(user_id: str, provider: str, api_key: str, label: str = "") -> dict:
    """Insert or update a provider API key for a user."""
    conn = _get_conn()
    now = time.time()
    existing = conn.execute(
        "SELECT id FROM provider_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    ).fetchone()

    if existing:
        conn.execute(
            "UPDATE provider_keys SET api_key = ?, label = ?, updated_at = ? WHERE id = ?",
            (api_key, label, now, existing["id"]),
        )
        conn.commit()
        return {"id": existing["id"], "provider": provider, "label": label, "updated_at": now}

    key_id = str(uuid.uuid4())
    conn.execute(
        "INSERT INTO provider_keys (id, user_id, provider, api_key, label, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (key_id, user_id, provider, api_key, label, now, now),
    )
    conn.commit()
    return {"id": key_id, "provider": provider, "label": label, "created_at": now}


def get_provider_keys(user_id: str) -> list[dict]:
    """Get all provider keys for a user (returns masked keys)."""
    conn = _get_conn()
    rows = conn.execute(
        "SELECT id, provider, api_key, label, created_at, updated_at FROM provider_keys WHERE user_id = ?",
        (user_id,),
    ).fetchall()
    return [dict(r) for r in rows]


def get_provider_key(user_id: str, provider: str) -> str | None:
    """Get the raw API key for a specific provider (for server-side use)."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT api_key FROM provider_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    ).fetchone()
    return row["api_key"] if row else None


def delete_provider_key(user_id: str, provider: str) -> bool:
    """Delete a provider key. Returns True if deleted."""
    conn = _get_conn()
    cursor = conn.execute(
        "DELETE FROM provider_keys WHERE user_id = ? AND provider = ?",
        (user_id, provider),
    )
    conn.commit()
    return cursor.rowcount > 0
