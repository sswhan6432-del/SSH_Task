"""Rate limiter and audit logging middleware for v2 API.

Sliding window rate limiting by API key:
- RPM (requests per minute)
- Tokens per hour
"""

import time
import threading
from collections import defaultdict

from services.audit_log import audit_logger


class RateLimiter:
    """Sliding window rate limiter."""

    def __init__(self, rpm: int = 60, tokens_per_hour: int = 1_000_000):
        self.rpm = rpm
        self.tokens_per_hour = tokens_per_hour
        self._request_windows: dict[str, list[float]] = defaultdict(list)
        self._token_windows: dict[str, list[tuple[float, int]]] = defaultdict(list)
        self._lock = threading.Lock()

    def _clean_window(self, window: list, cutoff: float):
        """Remove entries older than cutoff."""
        while window and (window[0] if isinstance(window[0], (int, float)) else window[0][0]) < cutoff:
            window.pop(0)

    def check_rpm(self, key_hash: str) -> bool:
        """Check if request is within RPM limit. Returns True if allowed."""
        now = time.time()
        with self._lock:
            window = self._request_windows[key_hash]
            self._clean_window(window, now - 60)
            if len(window) >= self.rpm:
                return False
            window.append(now)
            return True

    def check_tokens(self, key_hash: str, tokens: int) -> bool:
        """Check if token usage is within hourly limit. Returns True if allowed."""
        now = time.time()
        with self._lock:
            window = self._token_windows[key_hash]
            # Remove entries older than 1 hour
            while window and window[0][0] < now - 3600:
                window.pop(0)
            total = sum(t for _, t in window)
            if total + tokens > self.tokens_per_hour:
                return False
            window.append((now, tokens))
            return True

    def get_usage(self, key_hash: str) -> dict:
        """Get current usage stats for a key."""
        now = time.time()
        with self._lock:
            req_window = self._request_windows.get(key_hash, [])
            tok_window = self._token_windows.get(key_hash, [])

            recent_requests = sum(1 for t in req_window if t > now - 60)
            recent_tokens = sum(t for ts, t in tok_window if ts > now - 3600)

            return {
                "rpm_used": recent_requests,
                "rpm_limit": self.rpm,
                "tokens_hour_used": recent_tokens,
                "tokens_hour_limit": self.tokens_per_hour,
            }


def log_request(key_hash: str, endpoint: str, method: str,
                tokens: int = 0, latency_ms: float = 0.0,
                status_code: int = 200):
    """Log a request to the audit log."""
    audit_logger.log(
        api_key_hash=key_hash,
        endpoint=endpoint,
        method=method,
        tokens=tokens,
        latency_ms=latency_ms,
        status_code=status_code,
    )


# Singleton
rate_limiter = RateLimiter()
