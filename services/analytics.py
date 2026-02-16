"""Analytics aggregation for enterprise dashboard.

Produces heatmap data (24h x 7d), latency percentiles,
cost trends, and burn rate projection from task_history.json
and data/token_usage.json.
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import (
    HISTORY_FILE, TOKEN_USAGE_FILE,
    ROUTE_COST_PER_1K, ROUTE_TOKENS_PER_TASK,
    DEFAULT_COST_PER_1K, DEFAULT_TOKENS_PER_TASK,
)


def _read_json(path, default=None):
    if default is None:
        default = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return default


def _get_entries():
    data = _read_json(HISTORY_FILE, [])
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("entries", data.get("history", []))
    return []


def _get_token_usage():
    return _read_json(TOKEN_USAGE_FILE, [])


def _period_seconds(period: str) -> float:
    mapping = {"1h": 3600, "24h": 86400, "7d": 604800, "30d": 2592000}
    return mapping.get(period, 86400)


def get_usage_heatmap(period: str = "7d") -> list[list[int]]:
    """Generate 24h x 7d heatmap grid of request counts."""
    entries = _get_entries()
    grid = [[0] * 24 for _ in range(7)]  # 7 days x 24 hours
    cutoff = time.time() - _period_seconds(period)

    for entry in entries:
        ts = entry.get("timestamp", 0)
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts).timestamp()
            except (ValueError, TypeError):
                continue
        if ts < cutoff:
            continue
        dt = datetime.fromtimestamp(ts)
        day = dt.weekday()  # 0=Mon, 6=Sun
        hour = dt.hour
        if 0 <= day < 7 and 0 <= hour < 24:
            grid[day][hour] += 1

    return grid


def get_latency_percentiles(period: str = "24h") -> dict:
    """Calculate p50, p95, p99 latency from usage data."""
    usage = _get_token_usage()
    cutoff = time.time() - _period_seconds(period)
    latencies = []

    for entry in usage:
        ts = entry.get("timestamp", 0)
        if ts < cutoff:
            continue
        lat = entry.get("latency_ms", 0)
        if lat > 0:
            latencies.append(lat)

    if not latencies:
        return {"p50": 0, "p95": 0, "p99": 0, "count": 0}

    latencies.sort()
    n = len(latencies)
    return {
        "p50": latencies[int(n * 0.50)],
        "p95": latencies[min(int(n * 0.95), n - 1)],
        "p99": latencies[min(int(n * 0.99), n - 1)],
        "count": n,
    }


def get_cost_trends(period: str = "7d") -> list[dict]:
    """Aggregate cost per day/hour depending on period."""
    entries = _get_entries()
    cutoff = time.time() - _period_seconds(period)

    # Group by day
    daily = defaultdict(float)
    for entry in entries:
        ts = entry.get("timestamp", 0)
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts).timestamp()
            except (ValueError, TypeError):
                continue
        if ts < cutoff:
            continue

        dt = datetime.fromtimestamp(ts)
        day_key = dt.strftime("%Y-%m-%d")

        tasks = entry.get("tasks", [{"route": entry.get("route", "claude")}])
        for t in tasks:
            r = t.get("route", "claude")
            tk = ROUTE_TOKENS_PER_TASK.get(r, DEFAULT_TOKENS_PER_TASK)
            daily[day_key] += (tk / 1000) * ROUTE_COST_PER_1K.get(r, DEFAULT_COST_PER_1K)

    result = [{"date": k, "cost": round(v, 4)} for k, v in sorted(daily.items())]
    return result


def get_model_distribution(period: str = "7d") -> dict[str, int]:
    """Count requests per model/route."""
    entries = _get_entries()
    cutoff = time.time() - _period_seconds(period)
    counts = defaultdict(int)

    for entry in entries:
        ts = entry.get("timestamp", 0)
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts).timestamp()
            except (ValueError, TypeError):
                continue
        if ts < cutoff:
            continue

        tasks = entry.get("tasks", [{"route": entry.get("route", "claude")}])
        for t in tasks:
            r = t.get("route", "claude")
            counts[r] += 1

    return dict(counts)


def get_burn_rate(period: str = "30d") -> dict:
    """Calculate token burn rate and projection."""
    usage = _get_token_usage()
    cutoff = time.time() - _period_seconds(period)
    period_secs = _period_seconds(period)

    total_tokens = 0
    total_cost = 0.0
    count = 0

    for entry in usage:
        ts = entry.get("timestamp", 0)
        if ts < cutoff:
            continue
        total_tokens += entry.get("tokens", 0)
        total_cost += entry.get("cost", 0.0)
        count += 1

    if period_secs == 0:
        daily_rate = 0
    else:
        days = period_secs / 86400
        daily_rate = total_tokens / days if days > 0 else 0

    return {
        "total_tokens": total_tokens,
        "total_cost": round(total_cost, 4),
        "request_count": count,
        "daily_token_rate": round(daily_rate),
        "monthly_projection": round(daily_rate * 30),
        "monthly_cost_projection": round(total_cost / max(1, period_secs / 86400) * 30, 2),
    }


def get_dashboard_data(period: str = "24h") -> dict:
    """Aggregate all analytics data for dashboard."""
    return {
        "heatmap": get_usage_heatmap(period),
        "latency": get_latency_percentiles(period),
        "cost_trends": get_cost_trends(period),
        "model_distribution": get_model_distribution(period),
        "burn_rate": get_burn_rate(period),
        "period": period,
        "generated_at": time.time(),
    }
