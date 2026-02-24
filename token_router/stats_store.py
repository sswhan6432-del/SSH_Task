"""Persistent stats storage - survives server restarts."""

from __future__ import annotations

import json
import logging
import os
import threading

logger = logging.getLogger(__name__)

STATS_FILE = os.path.join(os.path.dirname(__file__), "stats.json")

_lock = threading.Lock()

_stats = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "total_savings_usd": 0.0,
    "requests_by_provider": {},
    "requests_by_model": {},
    "latency_sum_ms": 0.0,
}

# Save interval: flush to disk every N requests
_FLUSH_EVERY = 5
_since_last_flush = 0


def _load() -> None:
    """Load stats from disk on startup."""
    global _stats
    if not os.path.exists(STATS_FILE):
        return
    try:
        with open(STATS_FILE, "r") as f:
            saved = json.load(f)
        _stats.update(saved)
        logger.info("Stats loaded: %d requests, $%.4f cost",
                     _stats["total_requests"], _stats["total_cost_usd"])
    except Exception as e:
        logger.warning("Failed to load stats: %s", e)


def _flush() -> None:
    """Write stats to disk."""
    try:
        with open(STATS_FILE, "w") as f:
            json.dump(_stats, f, indent=2)
    except Exception as e:
        logger.warning("Failed to save stats: %s", e)


def get() -> dict:
    """Return a copy of current stats."""
    with _lock:
        return _stats.copy()


def record_request(
    provider: str,
    model_id: str,
    tokens: int,
    cost: float,
    latency_ms: float,
) -> None:
    """Record a completed request and periodically flush to disk."""
    global _since_last_flush
    with _lock:
        _stats["total_requests"] += 1
        _stats["total_tokens"] += tokens
        _stats["total_cost_usd"] += cost
        _stats["latency_sum_ms"] += latency_ms
        _stats["requests_by_provider"][provider] = _stats["requests_by_provider"].get(provider, 0) + 1
        _stats["requests_by_model"][model_id] = _stats["requests_by_model"].get(model_id, 0) + 1

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
