"""Usage monitoring endpoints (Zero-Knowledge compatible).

The server does NOT read API keys from the database.
The browser decrypts the key client-side and sends it via
X-Provider-Key header for one-time use per request.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request

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


def _get_provider_key(request: Request) -> str:
    """Extract the decrypted provider key from request header."""
    return request.headers.get("x-provider-key", "").strip()


@router.get("/anthropic")
async def get_anthropic_usage(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch Anthropic usage data. Key provided via X-Provider-Key header."""
    api_key = _get_provider_key(request)
    if not api_key:
        return {"status": "no_key", "provider": "anthropic", "message": "No API key provided. Decrypt and send via header."}
    return await fetch_anthropic_usage(api_key, days)


@router.get("/openai")
async def get_openai_usage(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch OpenAI usage data. Key provided via X-Provider-Key header."""
    api_key = _get_provider_key(request)
    if not api_key:
        return {"status": "no_key", "provider": "openai", "message": "No API key provided. Decrypt and send via header."}
    return await fetch_openai_usage(api_key, days)


@router.get("/deepseek")
async def get_deepseek_balance(
    request: Request,
    user_id: str = Depends(get_current_user_id),
):
    """Fetch DeepSeek account balance. Key provided via X-Provider-Key header."""
    api_key = _get_provider_key(request)
    if not api_key:
        return {"status": "no_key", "provider": "deepseek", "message": "No API key provided. Decrypt and send via header."}
    return await fetch_deepseek_balance(api_key)


@router.get("/all")
async def get_all_usage(
    request: Request,
    days: int = Query(default=30, ge=1, le=90),
    user_id: str = Depends(get_current_user_id),
):
    """Fetch usage summary. Keys provided as JSON in X-Provider-Keys header.

    Header format: {"anthropic":"sk-...","openai":"sk-...","deepseek":"sk-..."}
    """
    import json
    raw = request.headers.get("x-provider-keys", "")
    keys = {}
    if raw:
        try:
            keys = json.loads(raw)
        except json.JSONDecodeError:
            pass

    results = {}

    if keys.get("anthropic"):
        results["anthropic"] = await fetch_anthropic_usage(keys["anthropic"], days)
    else:
        results["anthropic"] = {"status": "no_key", "provider": "anthropic"}

    if keys.get("openai"):
        results["openai"] = await fetch_openai_usage(keys["openai"], days)
    else:
        results["openai"] = {"status": "no_key", "provider": "openai"}

    if keys.get("deepseek"):
        results["deepseek"] = await fetch_deepseek_balance(keys["deepseek"])
    else:
        results["deepseek"] = {"status": "no_key", "provider": "deepseek"}

    results["google"] = {
        "status": "console_only", "provider": "google",
        "console_url": CONSOLE_LINKS["google"],
        "message": "Google AI Studio does not provide a usage API.",
    }
    results["groq"] = {
        "status": "console_only", "provider": "groq",
        "console_url": CONSOLE_LINKS["groq"],
        "message": "Groq does not provide a usage API.",
    }

    return {"providers": results, "period_days": days}
