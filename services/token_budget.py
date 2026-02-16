"""Token budget management with tiktoken-based counting.

Tracks token usage per budget period, alerts at thresholds,
and stores state in data/token_budgets.json.
"""

import json
import os
import threading
import time
from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    import tiktoken
    _encoder = tiktoken.get_encoding("cl100k_base")
except ImportError:
    _encoder = None

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
BUDGETS_FILE = os.path.join(DATA_DIR, "token_budgets.json")

_lock = threading.Lock()


def count_tokens(text: str) -> int:
    """Count tokens using tiktoken cl100k_base encoding."""
    if _encoder is None:
        return len(text.split()) * 4 // 3  # rough fallback
    return len(_encoder.encode(text))


@dataclass
class TokenBudget:
    name: str
    limit: int  # max tokens per period
    used: int = 0
    period: str = "monthly"  # daily, weekly, monthly
    created_at: float = field(default_factory=time.time)
    reset_at: float = 0.0
    alerts: list = field(default_factory=list)

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    @property
    def usage_pct(self) -> float:
        if self.limit == 0:
            return 0.0
        return round(self.used / self.limit * 100, 1)

    def check_alerts(self) -> Optional[str]:
        """Check budget thresholds, return alert message if threshold crossed."""
        pct = self.usage_pct
        for threshold in [80, 90, 100]:
            if pct >= threshold and threshold not in self.alerts:
                self.alerts.append(threshold)
                return f"Budget '{self.name}' reached {threshold}% ({self.used:,}/{self.limit:,} tokens)"
        return None

    def consume(self, tokens: int) -> Optional[str]:
        """Add tokens to usage, return alert if threshold crossed."""
        self.used += tokens
        return self.check_alerts()

    def to_dict(self) -> dict:
        return asdict(self)


class BudgetManager:
    """Manages multiple token budgets with JSON persistence."""

    def __init__(self):
        self._budgets: dict[str, TokenBudget] = {}
        self._load()

    def _load(self):
        try:
            with open(BUDGETS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for name, bdata in data.items():
                self._budgets[name] = TokenBudget(**bdata)
        except (FileNotFoundError, json.JSONDecodeError, TypeError):
            pass

    def _save_unlocked(self):
        """Write to disk. Caller must hold _lock."""
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(BUDGETS_FILE, "w", encoding="utf-8") as f:
            json.dump({n: b.to_dict() for n, b in self._budgets.items()}, f, indent=2)

    def _save(self):
        with _lock:
            self._save_unlocked()

    def create(self, name: str, limit: int, period: str = "monthly") -> TokenBudget:
        if not name or not name.strip():
            raise ValueError("Budget name cannot be empty")
        if limit <= 0:
            raise ValueError("Budget limit must be positive")
        if period not in ("daily", "weekly", "monthly"):
            raise ValueError("Period must be daily, weekly, or monthly")
        with _lock:
            budget = TokenBudget(name=name.strip(), limit=limit, period=period)
            self._budgets[name.strip()] = budget
            self._save_unlocked()
        return budget

    def get(self, name: str) -> Optional[TokenBudget]:
        return self._budgets.get(name)

    def get_all(self) -> dict[str, dict]:
        return {n: b.to_dict() for n, b in self._budgets.items()}

    def consume(self, name: str, tokens: int) -> Optional[str]:
        """Atomic consume: lock held for entire read-modify-write cycle."""
        with _lock:
            budget = self._budgets.get(name)
            if not budget:
                return None
            alert = budget.consume(tokens)
            self._save_unlocked()
            return alert

    def delete(self, name: str) -> bool:
        with _lock:
            if name in self._budgets:
                del self._budgets[name]
                self._save_unlocked()
                return True
        return False

    def summary(self) -> list[dict]:
        results = []
        for name, b in self._budgets.items():
            results.append({
                "name": name,
                "limit": b.limit,
                "used": b.used,
                "remaining": b.remaining,
                "usage_pct": b.usage_pct,
                "period": b.period,
            })
        return results


# Singleton
budget_manager = BudgetManager()
