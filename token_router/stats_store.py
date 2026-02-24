"""Persistent stats storage - survives server restarts."""

from __future__ import annotations

import json
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")
REQUEST_LOG_FILE = os.path.join(os.path.dirname(__file__), "request_log.jsonl")

_lock = threading.Lock()

MAX_LOG_ENTRIES = 2000  # Keep last N requests in memory

_stats = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "total_savings_usd": 0.0,
    "requests_by_provider": {},
    "requests_by_model": {},
    "latency_sum_ms": 0.0,
}

# Per-request detail log (for Claude analytics)
_request_log: list[dict] = []

_FLUSH_EVERY = 5
_since_last_flush = 0


def _load() -> None:
    """Load stats and request log from disk on startup."""
    global _stats, _request_log
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r") as f:
                saved = json.load(f)
            _stats.update(saved)
            logger.info("Stats loaded: %d requests, $%.4f cost",
                         _stats["total_requests"], _stats["total_cost_usd"])
        except Exception as e:
            logger.warning("Failed to load stats: %s", e)

    if os.path.exists(REQUEST_LOG_FILE):
        try:
            entries = []
            with open(REQUEST_LOG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        entries.append(json.loads(line))
            _request_log = entries[-MAX_LOG_ENTRIES:]
            logger.info("Request log loaded: %d entries", len(_request_log))
        except Exception as e:
            logger.warning("Failed to load request log: %s", e)


def _flush() -> None:
    """Write stats to disk."""
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(_stats, f, indent=2)
    except Exception as e:
        logger.warning("Failed to save stats: %s", e)


def _append_log(entry: dict) -> None:
    """Append a request log entry to the JSONL file."""
    try:
        with open(REQUEST_LOG_FILE, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception as e:
        logger.warning("Failed to append request log: %s", e)


def get(user_id: str | None = None) -> dict:
    """Return a copy of current stats, optionally filtered by user_id.

    Admin/anonymous users see global stats. Regular users see only their own.
    """
    if user_id and user_id not in ("__admin__", "__anonymous__"):
        return _compute_user_stats(user_id)
    with _lock:
        return _stats.copy()


def _compute_user_stats(user_id: str) -> dict:
    """Compute stats from request log for a specific user."""
    with _lock:
        entries = [e for e in _request_log if e.get("user_id") == user_id]
    stats = {
        "total_requests": len(entries),
        "total_tokens": sum(e.get("total_tokens", 0) for e in entries),
        "total_cost_usd": sum(e.get("cost_usd", 0) for e in entries),
        "total_savings_usd": 0.0,
        "requests_by_provider": {},
        "requests_by_model": {},
        "latency_sum_ms": sum(e.get("latency_ms", 0) for e in entries),
    }
    for e in entries:
        p = e.get("provider", "unknown")
        m = e.get("model", "unknown")
        stats["requests_by_provider"][p] = stats["requests_by_provider"].get(p, 0) + 1
        stats["requests_by_model"][m] = stats["requests_by_model"].get(m, 0) + 1
    return stats


def get_request_log(limit: int = 500, provider: str = None, user_id: str | None = None) -> list[dict]:
    """Return recent request log entries, optionally filtered by provider and/or user_id."""
    with _lock:
        log = _request_log
        if user_id and user_id not in ("__admin__", "__anonymous__"):
            log = [e for e in log if e.get("user_id") == user_id]
        if provider:
            log = [e for e in log if e.get("provider") == provider]
        return log[-limit:]


def record_request(
    provider: str,
    model_id: str,
    tokens: int,
    cost: float,
    latency_ms: float,
    *,
    input_tokens: int = 0,
    output_tokens: int = 0,
    intent: str = "",
    difficulty: str = "",
    user_id: str = "__anonymous__",
) -> None:
    """Record a completed request with full details including user_id."""
    global _since_last_flush
    entry = {
        "ts": time.time(),
        "provider": provider,
        "model": model_id,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": tokens,
        "cost_usd": cost,
        "latency_ms": round(latency_ms, 1),
        "intent": intent,
        "difficulty": difficulty,
        "user_id": user_id,
    }

    with _lock:
        _stats["total_requests"] += 1
        _stats["total_tokens"] += tokens
        _stats["total_cost_usd"] += cost
        _stats["latency_sum_ms"] += latency_ms
        _stats["requests_by_provider"][provider] = _stats["requests_by_provider"].get(provider, 0) + 1
        _stats["requests_by_model"][model_id] = _stats["requests_by_model"].get(model_id, 0) + 1

        _request_log.append(entry)
        if len(_request_log) > MAX_LOG_ENTRIES:
            _request_log.pop(0)

        _append_log(entry)

        _since_last_flush += 1
        if _since_last_flush >= _FLUSH_EVERY:
            _flush()
            _since_last_flush = 0


def force_flush() -> None:
    """Force write to disk (called on shutdown)."""
    with _lock:
        _flush()


# Load on import
_load()
