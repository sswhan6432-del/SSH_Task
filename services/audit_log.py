"""Request audit logging for enterprise API.

Logs each request with timestamp, api_key hash, endpoint,
token count, and latency to data/audit_log.json.
"""

import atexit
import json
import os
import threading
import time
from collections import deque

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
AUDIT_FILE = os.path.join(DATA_DIR, "audit_log.json")

_lock = threading.Lock()
MAX_ENTRIES = 10000
SAVE_INTERVAL = 10  # save every N entries


class AuditLogger:
    """In-memory + file-backed audit log with atexit flush."""

    def __init__(self):
        self._entries: deque = deque(maxlen=MAX_ENTRIES)
        self._unsaved_count = 0
        self._load()
        atexit.register(self.flush)

    def _load(self):
        try:
            with open(AUDIT_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for entry in data[-MAX_ENTRIES:]:
                self._entries.append(entry)
        except (FileNotFoundError, json.JSONDecodeError):
            pass

    def _save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with _lock:
            tmp_file = AUDIT_FILE + ".tmp"
            try:
                with open(tmp_file, "w", encoding="utf-8") as f:
                    json.dump(list(self._entries), f, indent=2)
                os.replace(tmp_file, AUDIT_FILE)
            except OSError:
                try:
                    with open(AUDIT_FILE, "w", encoding="utf-8") as f:
                        json.dump(list(self._entries), f, indent=2)
                except OSError:
                    pass
            self._unsaved_count = 0

    def log(self, api_key_hash: str, endpoint: str, method: str,
            tokens: int = 0, latency_ms: float = 0.0, status_code: int = 200,
            extra: dict = None):
        """Log a single API request."""
        entry = {
            "timestamp": time.time(),
            "api_key_hash": api_key_hash[:12] if api_key_hash else "anonymous",
            "endpoint": endpoint,
            "method": method,
            "tokens": tokens,
            "latency_ms": round(latency_ms, 1),
            "status_code": status_code,
        }
        if extra:
            entry["extra"] = extra
        self._entries.append(entry)
        self._unsaved_count += 1

        if self._unsaved_count >= SAVE_INTERVAL:
            self._save()

    def get_recent(self, limit: int = 100) -> list[dict]:
        """Get most recent log entries."""
        entries = list(self._entries)
        return entries[-limit:]

    def flush(self):
        """Force save to disk (called on process exit)."""
        if self._unsaved_count > 0:
            self._save()


# Singleton
audit_logger = AuditLogger()
