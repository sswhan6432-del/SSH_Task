"""GET /v1/stats/claude - Claude-specific analytics endpoint."""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import APIRouter, Request

from token_router import stats_store
from token_router.providers.registry import MODELS

router = APIRouter()

# Anthropic model IDs for filtering
CLAUDE_MODELS = {"anthropic/claude-opus", "anthropic/claude-sonnet", "anthropic/claude-haiku"}

# What Opus would cost (for savings calculation)
OPUS_PRICING = MODELS["anthropic/claude-opus"].pricing


@router.get("/v1/stats/claude")
async def claude_analytics(request: Request):
    """Claude-specific analytics filtered by authenticated user."""
    user_id = getattr(request.state, "user_id", None)
    all_log = stats_store.get_request_log(limit=2000, user_id=user_id)
    overall = stats_store.get(user_id=user_id)

    # Filter Claude requests
    claude_log = [e for e in all_log if e.get("provider") == "anthropic"]
    all_providers_log = all_log

    # ── Per-Model Breakdown ─────────────────────────────────
    model_stats = {}
    for mid in CLAUDE_MODELS:
        entries = [e for e in claude_log if e.get("model") == mid]
        if not entries:
            model_stats[mid] = {
                "requests": 0, "total_tokens": 0, "input_tokens": 0,
                "output_tokens": 0, "cost_usd": 0, "avg_latency_ms": 0,
            }
            continue
        model_stats[mid] = {
            "requests": len(entries),
            "total_tokens": sum(e["total_tokens"] for e in entries),
            "input_tokens": sum(e["input_tokens"] for e in entries),
            "output_tokens": sum(e["output_tokens"] for e in entries),
            "cost_usd": round(sum(e["cost_usd"] for e in entries), 6),
            "avg_latency_ms": round(sum(e["latency_ms"] for e in entries) / len(entries), 1),
        }

    # ── Cost Optimization Analysis ──────────────────────────
    # "If ALL requests went to Opus, how much would it cost?"
    total_input = sum(e["input_tokens"] for e in all_providers_log)
    total_output = sum(e["output_tokens"] for e in all_providers_log)
    actual_cost = sum(e["cost_usd"] for e in all_providers_log)
    opus_cost = OPUS_PRICING.estimate(total_input, total_output)
    savings = max(opus_cost - actual_cost, 0)

    # ── Intent Distribution ─────────────────────────────────
    intent_counts = defaultdict(int)
    difficulty_counts = defaultdict(int)
    for e in all_providers_log:
        if e.get("intent"):
            intent_counts[e["intent"]] += 1
        if e.get("difficulty"):
            difficulty_counts[e["difficulty"]] += 1

    # ── Hourly Timeline (last 24h) ──────────────────────────
    now = time.time()
    hourly = defaultdict(lambda: {"requests": 0, "tokens": 0, "cost": 0.0})
    for e in all_providers_log:
        age_h = int((now - e["ts"]) / 3600)
        if age_h < 24:
            hour_label = f"-{age_h}h"
            hourly[hour_label]["requests"] += 1
            hourly[hour_label]["tokens"] += e["total_tokens"]
            hourly[hour_label]["cost"] += e["cost_usd"]

    # Sort timeline
    timeline = []
    for h in range(23, -1, -1):
        label = f"-{h}h"
        data = hourly.get(label, {"requests": 0, "tokens": 0, "cost": 0.0})
        timeline.append({"hour": label, **data})

    # ── Provider Comparison ─────────────────────────────────
    provider_comparison = defaultdict(lambda: {
        "requests": 0, "tokens": 0, "cost": 0.0, "avg_latency": 0.0, "latency_sum": 0.0,
    })
    for e in all_providers_log:
        p = e["provider"]
        provider_comparison[p]["requests"] += 1
        provider_comparison[p]["tokens"] += e["total_tokens"]
        provider_comparison[p]["cost"] += e["cost_usd"]
        provider_comparison[p]["latency_sum"] += e["latency_ms"]

    for p in provider_comparison:
        n = provider_comparison[p]["requests"] or 1
        provider_comparison[p]["avg_latency"] = round(provider_comparison[p]["latency_sum"] / n, 1)
        provider_comparison[p]["cost"] = round(provider_comparison[p]["cost"], 6)
        del provider_comparison[p]["latency_sum"]

    # ── Top Models by Usage ─────────────────────────────────
    model_usage = defaultdict(int)
    for e in all_providers_log:
        model_usage[e["model"]] += 1
    top_models = sorted(model_usage.items(), key=lambda x: -x[1])[:10]

    return {
        "claude_models": model_stats,
        "cost_optimization": {
            "actual_cost_usd": round(actual_cost, 6),
            "opus_equivalent_usd": round(opus_cost, 6),
            "savings_usd": round(savings, 6),
            "savings_pct": round((savings / opus_cost * 100) if opus_cost > 0 else 0, 1),
        },
        "intent_distribution": dict(intent_counts),
        "difficulty_distribution": dict(difficulty_counts),
        "timeline_24h": timeline,
        "provider_comparison": dict(provider_comparison),
        "top_models": [{"model": m, "requests": c} for m, c in top_models],
        "total_requests_all": overall["total_requests"],
        "total_requests_claude": sum(s["requests"] for s in model_stats.values()),
    }
