"""Google Gemini provider adapter (Gemini API conversion)."""

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

GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

MODEL_MAP = {
    "gemini-2.5-pro": "gemini-2.5-pro-preview-06-05",
    "gemini-2.5-flash": "gemini-2.5-flash-preview-05-20",
}

AVAILABLE_MODELS = [
    ModelInfo(
        id="google/gemini-2.5-pro", name="Gemini 2.5 Pro", provider="google",
        max_tokens=8192, pricing=TokenPricing(1.25, 5.00), quality_tier=1,
    ),
    ModelInfo(
        id="google/gemini-2.5-flash", name="Gemini 2.5 Flash", provider="google",
        max_tokens=8192, pricing=TokenPricing(0.15, 0.60), quality_tier=2,
    ),
]


class GoogleAdapter(ProviderAdapter):
    """Converts OpenAI chat format to Google Gemini API."""

    provider_name = "google"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=GEMINI_BASE_URL,
            timeout=httpx.Timeout(settings.request_timeout, read=settings.stream_timeout),
        )
        self._default_key = settings.google_api_key

    def _resolve_key(self, api_key: Optional[str]) -> str:
        key = api_key or self._default_key
        if not key:
            raise ValueError("No Google API key. Pass X-Google-Key header or set GOOGLE_API_KEY env var.")
        return key

    def _resolve_model(self, model: str) -> str:
        return MODEL_MAP.get(model, model)

    def _convert_messages(self, messages: List[ChatMessage]) -> tuple[Optional[str], list]:
        """Convert OpenAI messages to Gemini contents format."""
        system_text = None
        contents = []

        for msg in messages:
            content_str = msg.content if isinstance(msg.content, str) else str(msg.content)
            if msg.role == "system":
                system_text = content_str
            elif msg.role == "user":
                contents.append({"role": "user", "parts": [{"text": content_str}]})
            elif msg.role == "assistant":
                contents.append({"role": "model", "parts": [{"text": content_str}]})

        return system_text, contents

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
        system_text, contents = self._convert_messages(messages)
        api_model = self._resolve_model(model)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
            },
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        url = f"/models/{api_model}:generateContent?key={self._resolve_key(api_key)}"
        resp = await self._client.post(url, json=payload)
        resp.raise_for_status()
        data = resp.json()

        content = ""
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            content = "".join(p.get("text", "") for p in parts)

        usage_meta = data.get("usageMetadata", {})

        return ChatCompletionResponse(
            id=f"chatcmpl-{uuid.uuid4().hex[:12]}",
            created=int(time.time()),
            model=f"google/{model}",
            choices=[
                Choice(
                    index=0,
                    message=ChatMessage(role="assistant", content=content),
                    finish_reason="stop",
                )
            ],
            usage=Usage(
                prompt_tokens=usage_meta.get("promptTokenCount", 0),
                completion_tokens=usage_meta.get("candidatesTokenCount", 0),
                total_tokens=usage_meta.get("totalTokenCount", 0),
            ),
            provider="google",
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
        system_text, contents = self._convert_messages(messages)
        api_model = self._resolve_model(model)

        payload: dict[str, Any] = {
            "contents": contents,
            "generationConfig": {"temperature": temperature},
        }
        if max_tokens:
            payload["generationConfig"]["maxOutputTokens"] = max_tokens
        if system_text:
            payload["systemInstruction"] = {"parts": [{"text": system_text}]}

        url = f"/models/{api_model}:streamGenerateContent?alt=sse&key={self._resolve_key(api_key)}"
        chunk_id = f"chatcmpl-{uuid.uuid4().hex[:12]}"
        created = int(time.time())

        async with self._client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line.startswith("data: "):
                    continue
                raw = line[6:]
                try:
                    event = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                candidates = event.get("candidates", [])
                if not candidates:
                    continue

                parts = candidates[0].get("content", {}).get("parts", [])
                text = "".join(p.get("text", "") for p in parts)

                finish = candidates[0].get("finishReason")

                if text:
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": f"google/{model}",
                        "choices": [{
                            "index": 0,
                            "delta": {"content": text},
                            "finish_reason": None,
                        }],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"

                if finish == "STOP":
                    chunk = {
                        "id": chunk_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": f"google/{model}",
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
            if m.id == f"google/{model}" or m.id == model:
                return m.pricing
        return TokenPricing(1.25, 5.00)

    async def health_check(self) -> bool:
        if not self._default_key:
            return False
        try:
            url = f"/models?key={self._default_key}"
            resp = await self._client.get(url)
            return resp.status_code == 200
        except Exception:
            return False
