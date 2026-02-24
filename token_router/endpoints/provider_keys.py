"""Provider API key management endpoints (Zero-Knowledge Encryption).

The server stores only AES-256-GCM encrypted blobs.
Encryption/decryption happens exclusively in the browser.
The server NEVER sees plaintext API keys.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from token_router import db
from token_router.auth import get_current_user_id

router = APIRouter(prefix="/v1/settings", tags=["Settings"])

VALID_PROVIDERS = {"anthropic", "openai", "deepseek", "google", "groq"}


class EncryptedKeyRequest(BaseModel):
    encrypted_key: str  # AES-256-GCM encrypted, base64-encoded
    label: str = ""


@router.get("/keys")
async def list_keys(user_id: str = Depends(get_current_user_id)):
    """List all saved provider keys (encrypted blobs) for the current user."""
    rows = db.get_provider_keys(user_id)
    keys = [
        {
            "id": r["id"],
            "provider": r["provider"],
            "encrypted_key": r["api_key"],  # This IS the encrypted blob
            "label": r["label"],
            "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }
        for r in rows
    ]
    return {"keys": keys}


@router.put("/keys/{provider}")
async def upsert_key(
    provider: str,
    body: EncryptedKeyRequest,
    user_id: str = Depends(get_current_user_id),
):
    """Store an encrypted API key blob. Server cannot decrypt this."""
    if provider not in VALID_PROVIDERS:
        return {"error": f"Invalid provider. Must be one of: {', '.join(sorted(VALID_PROVIDERS))}"}

    # Store the encrypted blob as-is (server treats it as opaque data)
    result = db.upsert_provider_key(user_id, provider, body.encrypted_key, body.label or "")
    return {"status": "ok", "provider": provider, **result}


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
