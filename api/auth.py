"""API key authentication for v2 endpoints.

Keys stored as SHA256 hashes in data/api_keys.json.
"""

import hashlib
import json
import os
import secrets
import threading
import time
from functools import wraps

from flask import request, jsonify

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
KEYS_FILE = os.path.join(DATA_DIR, "api_keys.json")

_lock = threading.Lock()


def _hash_key(key: str) -> str:
    return hashlib.sha256(key.encode()).hexdigest()


def _load_keys() -> dict:
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save_keys(data: dict):
    os.makedirs(DATA_DIR, exist_ok=True)
    with _lock:
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def generate_api_key(name: str = "default") -> dict:
    """Generate a new API key. Returns the raw key (shown once) and metadata."""
    raw_key = f"ssh_{secrets.token_hex(24)}"
    key_hash = _hash_key(raw_key)

    keys = _load_keys()
    keys[key_hash] = {
        "name": name,
        "created_at": time.time(),
        "last_used": 0,
        "request_count": 0,
    }
    _save_keys(keys)

    return {
        "key": raw_key,
        "key_hash": key_hash[:12] + "...",
        "name": name,
    }


def validate_key(raw_key: str) -> dict | None:
    """Validate an API key. Returns key metadata or None."""
    key_hash = _hash_key(raw_key)
    keys = _load_keys()
    meta = keys.get(key_hash)
    if meta:
        meta["last_used"] = time.time()
        meta["request_count"] = meta.get("request_count", 0) + 1
        keys[key_hash] = meta
        _save_keys(keys)
        return {"hash": key_hash, **meta}
    return None


def revoke_key(key_hash: str) -> bool:
    """Revoke an API key by its hash."""
    keys = _load_keys()
    if key_hash in keys:
        del keys[key_hash]
        _save_keys(keys)
        return True
    return False


def list_keys() -> list[dict]:
    """List all API keys (hashes only, not raw keys)."""
    keys = _load_keys()
    result = []
    for h, meta in keys.items():
        result.append({
            "key_hash": h[:12] + "...",
            "name": meta.get("name", "unknown"),
            "created_at": meta.get("created_at", 0),
            "last_used": meta.get("last_used", 0),
            "request_count": meta.get("request_count", 0),
        })
    return result


def require_api_key(f):
    """Decorator to require valid API key via Bearer token."""
    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"error": "Missing API key. Use Authorization: Bearer <key>"}), 401

        raw_key = auth_header[7:].strip()
        meta = validate_key(raw_key)
        if not meta:
            return jsonify({"error": "Invalid API key"}), 401

        # Attach key metadata to request context
        request.api_key_meta = meta
        return f(*args, **kwargs)

    return decorated
