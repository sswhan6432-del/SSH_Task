"""Anthropic provider adapter (Messages API conversion)."""

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

ANTHROPIC_BASE_URL = "https://api.anthropic.com/v1"
ANTHROPIC_VERSION = "2023-06-01"

MODEL_MAP = {
    "claude-opus": "claude-opus-4-20250514",
    "claude-sonnet": "claude-sonnet-4-20250514",
    "claude-haiku": "claude-haiku-4-5-20251001",
}

AVAILABLE_MODELS = [
    ModelInfo(
        id="anthropic/claude-opus", name="Claude Opus 4", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(15.00, 75.00), quality_tier=1,
    ),
    ModelInfo(
        id="anthropic/claude-sonnet", name="Claude Sonnet 4", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(3.00, 15.00), quality_tier=1,
    ),
    ModelInfo(
        id="anthropic/claude-haiku", name="Claude Haiku 3.5", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(0.80, 4.00), quality_tier=2,
    ),
]


class AnthropicAdapter(ProviderAdapter):
    """Converts OpenAI chat format to Anthropic Messages API."""

    provider_name = "anthropic"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=ANTHROPIC_BASE_URL,
            headers={
                "anthropic-version": ANTHROPIC_VERSION,
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(settings.request_timeout, read=settings.stream_timeout),
        )
        self._default_key = settings.anthropic_api_key

    def _resolve_key(self, api_key: Optional[str]) -> str:
        key = api_key or self._default_key
        if not key:
            raise ValueError("No Anthropic API key. Pass X-Anthropic-Key header or set ANTHROPIC_API_KEY env var.")
        return key

    def _resolve_model(self, model: str) -> str:
        return MODEL_MAP.get(model, model)

    def _auth_headers(self, api_key: Optional[str]) -> dict:
        return {"x-api-key": self._resolve_key(api_key)}

    def _convert_messages(self, messages: List[ChatMessage]) -> tuple[Optional[str], list]:
        """Convert OpenAI messages to Anthropic format."""
        system_text = None
        api_messages = []

        for msg in messages:
            if msg.role == "system":
                system_text = msg.content if isinstance(msg.content, str) else str(msg.content)
            else:
                content = msg.content if isinstance(msg.content, str) else str(msg.content)
                api_messages.append({"role": msg.role, "content": content})

        return system_text, api_messages

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
        system_text, api_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self._resolve_model(model),
            "messages": api_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
        }
        if system_text:
            payload["system"] = system_text

        resp = await self._client.post(
            "/messages", json=payload, headers=self._auth_headers(api_key),
        )
        resp.raise_for_status()
        data = resp.json()

        content = ""
        for block in data.get("content", []):
            if block.get("type") == "text":
                content += block.get("text", "")

        usage_data = data.get("usage", {})

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=f"anthropic/{model}",
            choices=[
                Choice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop" if data.get("stop_reason") == "end_turn" else data.get("stop_reason", "stop"),
                )
            ],
            usage=Usage(
                prompt_tokens=usage_data.get("input_tokens", 0),
                completion_tokens=usage_data.get("output_tokens", 0),
                total_tokens=usage_data.get("input_tokens", 0) + usage_data.get("output_tokens", 0),
            ),
            provider="anthropic",
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
        system_text, api_messages = self._convert_messages(messages)

        payload: dict[str, Any] = {
            "model": self._resolve_model(model),
            "messages": api_messages,
            "max_tokens": max_tokens or 4096,
            "temperature": temperature,
            "stream": True,
        }
        if system_text:
            payload["system"] = system_text

        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())

        async with self._client.stream(
            "POST", "/messages", json=payload, headers=self._auth_headers(api_key),
        ) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                event_type = event.get("type", "")

                if event_type == "content_block_delta":
                    delta = event.get("delta", {})
                    text = delta.get("text", "")
                    if text:
                        chunk = {
                            "id": chunk_id,
                            "object": "chat.completion.chunk",
                            "created": created,
                            "model": f"anthropic/{model}",
                            "choices": [{
                                "index": 0,
                                "delta": {"content": text},
                                "finish_reason": None,
                            }],
                        }
                        yield f"data: {json.dumps(chunk)}\n\n"

                elif event_type == "message_stop":
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": f"anthropic/{model}",
                        "choices": [{
                            "index": 0,
                            "delta": {},
                            "finish_reason": "stop",
                        }],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    yield "data: [DONE]\n\n"

    def list_models(self) -> List[ModelInfo]:
        return AVAILABLE_MODELS

    def get_pricing(self, model: str) -> TokenPricing:
        for m in AVAILABLE_MODELS:
            if m.id == f"anthropic/{model}" or m.id == model:
                return m.pricing
        return TokenPricing(3.00, 15.00)

    async def health_check(self) -> bool:
        if not self._default_key:
            return False
        try:
            resp = await self._client.post(
                "/messages",
                json={
                    "model": "claude-haiku-4-5-20251001",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "hi"}],
                },
                headers=self._auth_headers(None),
            )
            return resp.status_code in (200, 429)
        except Exception:
            return False
