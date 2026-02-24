"""Groq provider adapter (OpenAI-compatible API)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any, AsyncIterator, List, Optional

import httpx

from token_router.config import settings
from token_router.models import (
    ChatCompletionResponse,
    ChatMessage,
    Choice,
    Usage,
)
from token_router.providers.base import ModelInfo, ProviderAdapter, TokenPricing

GROQ_BASE_URL = "https://api.groq.com/openai/v1"

MODEL_MAP = {
    "llama-3.3-70b": "llama-3.3-70b-versatile",
    "mixtral-8x7b": "mixtral-8x7b-32768",
}

AVAILABLE_MODELS = [
    ModelInfo(
        id="groq/llama-3.3-70b", name="Llama 3.3 70B", provider="groq",
        max_tokens=8192, pricing=TokenPricing(0.59, 0.79), quality_tier=2,
    ),
    ModelInfo(
        id="groq/mixtral-8x7b", name="Mixtral 8x7B", provider="groq",
        max_tokens=32768, pricing=TokenPricing(0.24, 0.24), quality_tier=3,
    ),
]


class GroqAdapter(ProviderAdapter):
    provider_name = "groq"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=GROQ_BASE_URL,
            headers={"Content-Type": "application/json"},
            timeout=httpx.Timeout(settings.request_timeout, read=settings.stream_timeout),
        )
        self._default_key = settings.groq_api_key

    def _resolve_key(self, api_key: Optional[str]) -> str:
        key = api_key or self._default_key
        if not key:
            raise ValueError("No Groq API key. Pass X-Groq-Key header or set GROQ_API_KEY env var.")
        return key

    def _resolve_model(self, model: str) -> str:
        return MODEL_MAP.get(model, model)

    def _auth_headers(self, api_key: Optional[str]) -> dict:
        return {"Authorization": f"Bearer {self._resolve_key(api_key)}"}

    async def chat_completion(
        self,
        messages: List[ChatMessage],
        model: str,
        *,
        api_key: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs: Any,
    ) -> ChatCompletionResponse:
        payload = {
            "model": self._resolve_model(model),
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        resp = await self._client.post(
            "/chat/completions", json=payload, headers=self._auth_headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()

        return ChatCompletionResponse(
            id=data.get("id", f"chatcmpl-{uuid.uuid4().hex[:12]}"),
            created=data.get("created", int(time.time())),
            model=f"groq/{model}",
            choices=[
                Choice(
                    index=c["index"],
                    message=ChatMessage(role=c["message"]["role"], content=c["message"]["content"]),
                    finish_reason=c.get("finish_reason", "stop"),
                )
                for c in data["choices"]
            ],
            usage=Usage(**(data.get("usage", {}))),
            provider="groq",
        )

    async def chat_completion_stream(
        self,
        messages: List[ChatMessage],
        model: str,
        *,
        api_key: Optional[str] = None,
        temperature: float = 1.0,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> AsyncIterator[str]:
        payload = {
            "model": self._resolve_model(model),
            "messages": [m.model_dump(exclude_none=True) for m in messages],
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens:
            payload["max_tokens"] = max_tokens

        async with self._client.stream(
            "POST", "/chat/completions", json=payload, headers=self._auth_headers(api_key),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if line.startswith("data: "):
                    chunk = line[6:]
                    if chunk.strip() == "[DONE]":
                        yield "data: [DONE]\n\n"
                        break
                    try:
                        obj = json.loads(chunk)
                        obj["model"] = f"groq/{model}"
                        yield f"data: {json.dumps(obj)}\n\n"
                    except json.JSONDecodeError:
                        yield f"data: {chunk}\n\n"

    def list_models(self) -> List[ModelInfo]:
        return AVAILABLE_MODELS

    def get_pricing(self, model: str) -> TokenPricing:
        for m in AVAILABLE_MODELS:
            if m.id == f"groq/{model}" or m.id == model:
                return m.pricing
        return TokenPricing(0.59, 0.79)

    async def health_check(self) -> bool:
        if not self._default_key:
            return False
        try:
            resp = await self._client.get("/models", headers=self._auth_headers(None))
            return resp.status_code == 200
        except Exception:
            return False
