"""Provider API key management endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from token_router import db
from token_router.auth import get_current_user_id
from token_router.models import ProviderKeyRequest, ProviderKeyResponse, ProviderKeysListResponse

router = APIRouter(prefix="/v1/settings", tags=["Settings"])

VALID_PROVIDERS = {"anthropic", "openai", "deepseek", "google", "groq"}


def _mask_key(key: str) -> str:
    """Mask an API key, showing only first 8 and last 4 chars."""
    if len(key) <= 12:
        return key[:4] + "..." + key[-2:]
    return key[:8] + "..." + key[-4:]


@router.get("/keys", response_model=ProviderKeysListResponse)
async def list_keys(user_id: str = Depends(get_current_user_id)):
    """List all saved provider keys (masked) for the current user."""
    rows = db.get_provider_keys(user_id)
    keys = [
        ProviderKeyResponse(
            id=r["id"],
            provider=r["provider"],
            masked_key=_mask_key(r["api_key"]),
            label=r["label"],
            created_at=r["created_at"],
            updated_at=r["updated_at"],
        )
        for r in rows
    ]
    return ProviderKeysListResponse(keys=keys)


@router.put("/keys/{provider}")
async def upsert_key(
    provider: str,
    body: ProviderKeyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Register or update a provider API key."""
    if provider not in VALID_PROVIDERS:
        return {"error": f"Invalid provider. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"}

    result = db.upsert_provider_key(user_id, provider, body.api_key, body.label or "")
    return {"status": "ok", "provider": provider, "masked_key": _mask_key(body.api_key), **result}


@router.delete("/keys/{provider}")
async def delete_key(
    provider: str,
    user_id: str = Depends(get_current_user_id),
):
    """Delete a provider API key."""
    deleted = db.delete_provider_key(user_id, provider)
    if not deleted:
        return {"status": "not_found", "provider": provider}
    return {"status": "deleted", "provider": provider}
