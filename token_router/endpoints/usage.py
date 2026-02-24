"""Usage monitoring endpoints - fetch data from provider APIs."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query

from token_router import db
from token_router.auth import get_current_user_id
from token_router.services.usage_fetcher import (
    fetch_anthropic_usage,
    fetch_deepseek_balance,
    fetch_openai_usage,
)

router = APIRouter(prefix="/v1/usage", tags=["Usage"])

CONSOLE_LINKS = {
    "google": "https://aistudio.google.com/usage",
    "groq": "https://console.groq.com/usage",
}


@router.get("/anthropic")
async def get_anthropic_usage(
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch Anthropic usage data using stored API key."""
    api_key = db.get_provider_key(user_id, "anthropic")
    if not api_key:
        return {"status": "no_key", "provider": "anthropic", "message": "No Anthropic API key configured. Add one in Settings."}
    return await fetch_anthropic_usage(api_key, days)


@router.get("/openai")
async def get_openai_usage(
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch OpenAI usage data using stored API key."""
    api_key = db.get_provider_key(user_id, "openai")
    if not api_key:
        return {"status": "no_key", "provider": "openai", "message": "No OpenAI API key configured. Add one in Settings."}
    return await fetch_openai_usage(api_key, days)


@router.get("/deepseek")
async def get_deepseek_balance(
    user_id: str = Depends(get_current_user_id),
):
    """Fetch DeepSeek account balance using stored API key."""
    api_key = db.get_provider_key(user_id, "deepseek")
    if not api_key:
        return {"status": "no_key", "provider": "deepseek", "message": "No DeepSeek API key configured. Add one in Settings."}
    return await fetch_deepseek_balance(api_key)


@router.get("/all")
async def get_all_usage(
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch usage summary for all configured providers."""
    keys = db.get_provider_keys(user_id)
    configured = {r["provider"] for r in keys}

    results = {}

    if "anthropic" in configured:
        results["anthropic"] = await fetch_anthropic_usage(
            db.get_provider_key(user_id, "anthropic"), days
        )
    else:
        results["anthropic"] = {"status": "no_key", "provider": "anthropic"}

    if "openai" in configured:
        results["openai"] = await fetch_openai_usage(
            db.get_provider_key(user_id, "openai"), days
        )
    else:
        results["openai"] = {"status": "no_key", "provider": "openai"}

    if "deepseek" in configured:
        results["deepseek"] = await fetch_deepseek_balance(
            db.get_provider_key(user_id, "deepseek")
        )
    else:
        results["deepseek"] = {"status": "no_key", "provider": "deepseek"}

    # Providers without usage APIs - provide console links
    results["google"] = {
        "status": "no_api" if "google" not in configured else "console_only",
        "provider": "google",
        "console_url": CONSOLE_LINKS["google"],
        "message": "Google AI Studio does not provide a usage API. Check the console.",
    }
    results["groq"] = {
        "status": "no_api" if "groq" not in configured else "console_only",
        "provider": "groq",
        "console_url": CONSOLE_LINKS["groq"],
        "message": "Groq does not provide a usage API. Check the console.",
    }

    return {"providers": results, "period_days": days}
