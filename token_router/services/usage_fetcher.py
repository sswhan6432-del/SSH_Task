"""Provider Usage API clients for fetching usage data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TIMEOUT = httpx.Timeout(15.0)


async def fetch_anthropic_usage(api_key: str, days: int = 30) -> dict[str, Any]:
    """Fetch Anthropic usage and cost reports.

    Requires an Admin API key (sk-ant-admin-*).
    Endpoints:
        GET /v1/organizations/usage - Token usage by model
        GET /v1/organizations/costs - Cost breakdown
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    # Anthropic usage API uses page-based daily buckets
    params = {
        "start_date": start.strftime("%Y-%m-%d"),
        "end_date": now.strftime("%Y-%m-%d"),
    }
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    result: dict[str, Any] = {
        "provider": "anthropic",
        "period_days": days,
        "status": "ok",
        "usage": None,
        "costs": None,
        "error": None,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Fetch usage report
        try:
            resp = await client.get(
                "https://api.anthropic.com/v1/organizations/usage",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                result["usage"] = resp.json()
            else:
                # Try the messages usage endpoint as fallback
                resp2 = await client.get(
                    "https://api.anthropic.com/v1/organizations/usage_report/messages",
                    params=params,
                    headers=headers,
                )
                if resp2.status_code == 200:
                    result["usage"] = resp2.json()
                else:
                    result["error"] = f"Usage API returned {resp.status_code}: {resp.text[:200]}"
                    result["status"] = "api_error"
        except httpx.HTTPError as e:
            result["error"] = f"Usage request failed: {str(e)}"
            result["status"] = "connection_error"
            return result

        # Fetch cost report
        try:
            resp = await client.get(
                "https://api.anthropic.com/v1/organizations/costs",
                params=params,
                headers=headers,
            )
            if resp.status_code == 200:
                result["costs"] = resp.json()
            else:
                # Try cost_report endpoint as fallback
                resp2 = await client.get(
                    "https://api.anthropic.com/v1/organizations/cost_report",
                    params=params,
                    headers=headers,
                )
                if resp2.status_code == 200:
                    result["costs"] = resp2.json()
        except httpx.HTTPError:
            pass  # Cost data is optional

    return result


async def fetch_openai_usage(api_key: str, days: int = 30) -> dict[str, Any]:
    """Fetch OpenAI usage data.

    Endpoints:
        GET /v1/organization/usage/completions - Chat completion usage
        GET /v1/organization/costs - Cost data
        GET /v1/usage - Legacy usage endpoint (daily token counts)
    """
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=days)

    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    result: dict[str, Any] = {
        "provider": "openai",
        "period_days": days,
        "status": "ok",
        "usage": None,
        "costs": None,
        "error": None,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        # Try the organization usage API first
        try:
            # New bucket-based usage API
            start_ts = int(start.timestamp())
            resp = await client.get(
                "https://api.openai.com/v1/organization/usage/completions",
                params={"start_time": start_ts, "limit": 31, "group_by": ["model"]},
                headers=headers,
            )
            if resp.status_code == 200:
                result["usage"] = resp.json()
            else:
                # Fallback: legacy /v1/usage endpoint (date-based)
                resp2 = await client.get(
                    "https://api.openai.com/v1/usage",
                    params={"date": now.strftime("%Y-%m-%d")},
                    headers=headers,
                )
                if resp2.status_code == 200:
                    result["usage"] = resp2.json()
                else:
                    result["error"] = f"Usage API returned {resp.status_code}: {resp.text[:200]}"
                    result["status"] = "api_error"
        except httpx.HTTPError as e:
            result["error"] = f"Usage request failed: {str(e)}"
            result["status"] = "connection_error"
            return result

        # Fetch costs
        try:
            resp = await client.get(
                "https://api.openai.com/v1/organization/costs",
                params={"start_time": int(start.timestamp()), "limit": 31, "group_by": ["model"]},
                headers=headers,
            )
            if resp.status_code == 200:
                result["costs"] = resp.json()
        except httpx.HTTPError:
            pass

    return result


async def fetch_deepseek_balance(api_key: str) -> dict[str, Any]:
    """Fetch DeepSeek account balance.

    Endpoint: GET /user/balance
    """
    headers = {
        "Authorization": f"Bearer {api_key}",
    }

    result: dict[str, Any] = {
        "provider": "deepseek",
        "status": "ok",
        "balance": None,
        "error": None,
    }

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        try:
            resp = await client.get(
                "https://api.deepseek.com/user/balance",
                headers=headers,
            )
            if resp.status_code == 200:
                result["balance"] = resp.json()
            else:
                result["error"] = f"Balance API returned {resp.status_code}: {resp.text[:200]}"
                result["status"] = "api_error"
        except httpx.HTTPError as e:
            result["error"] = f"Balance request failed: {str(e)}"
            result["status"] = "connection_error"

    return result
