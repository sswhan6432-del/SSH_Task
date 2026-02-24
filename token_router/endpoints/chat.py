"""POST /v1/chat/completions - OpenAI-compatible chat endpoint with BYOK."""

from __future__ import annotations

import json
import logging
import time
from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse

from token_router.models import (
    ChatCompletionRequest,
    ChatCompletionResponse,
    ErrorResponse,
    ErrorDetail,
)
from token_router.providers.registry import registry, MODELS
from token_router.router import route

logger = logging.getLogger(__name__)

router = APIRouter()

# In-memory stats accumulator
_stats = {
    "total_requests": 0,
    "total_tokens": 0,
    "total_cost_usd": 0.0,
    "total_savings_usd": 0.0,
    "requests_by_provider": {},
    "requests_by_model": {},
    "latency_sum_ms": 0.0,
}


def get_stats() -> dict:
    return _stats.copy()


@router.post("/v1/chat/completions")
async def chat_completions(req: ChatCompletionRequest, request: Request):
    """OpenAI-compatible chat completions endpoint.

    Model format: 'provider/model-name' (e.g., 'groq/llama-3.3-70b')
    Or set model='auto' to let TokenRouter pick the best model.

    BYOK: Pass your own API key via headers:
      X-OpenAI-Key, X-Anthropic-Key, X-Groq-Key, X-Google-Key, X-DeepSeek-Key
    """
    start = time.time()
    _stats["total_requests"] += 1

    # Extract user's provider API keys from headers
    from token_router.main import extract_user_provider_keys
    user_keys = extract_user_provider_keys(request)

    # Smart routing if requested
    model_id = req.model
    if req.auto_route or model_id == "auto":
        decision = route(req.messages, budget_cap=req.budget_cap)
        model_id = decision.recommended_models[0] if decision.recommended_models else "groq/llama-3.3-70b"

    # Resolve provider
    provider_name, model_name = registry.resolve_model(model_id)
    provider = registry.get_provider(model_id)

    if not provider:
        raise HTTPException(
            status_code=400,
            detail=ErrorResponse(
                error=ErrorDetail(
                    message=f"Provider '{provider_name}' not found.",
                    type="invalid_request_error",
                    code="provider_unavailable",
                )
            ).model_dump(),
        )

    # Resolve API key: user header > server default
    user_key = user_keys.get(provider_name)

    # Track by provider/model
    _stats["requests_by_provider"][provider_name] = _stats["requests_by_provider"].get(provider_name, 0) + 1
    _stats["requests_by_model"][model_id] = _stats["requests_by_model"].get(model_id, 0) + 1

    try:
        if req.stream:
            return await _handle_stream(provider, model_name, req, api_key=user_key)

        # Non-streaming
        response = await provider.chat_completion(
            messages=req.messages,
            model=model_name,
            api_key=user_key,
            temperature=req.temperature or 1.0,
            max_tokens=req.max_tokens,
            top_p=req.top_p,
            frequency_penalty=req.frequency_penalty,
            presence_penalty=req.presence_penalty,
            stop=req.stop,
        )

        # Calculate cost
        model_info = MODELS.get(model_id)
        if model_info and response.usage:
            cost = model_info.pricing.estimate(
                response.usage.prompt_tokens,
                response.usage.completion_tokens,
            )
            response.cost_usd = round(cost, 8)
            _stats["total_cost_usd"] += cost

        _stats["total_tokens"] += response.usage.total_tokens if response.usage else 0

        elapsed_ms = (time.time() - start) * 1000
        _stats["latency_sum_ms"] += elapsed_ms

        return response

    except ValueError as e:
        # Missing API key
        raise HTTPException(
            status_code=401,
            detail={
                "error": {
                    "message": str(e),
                    "type": "authentication_error",
                    "code": "missing_provider_key",
                }
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Chat completion failed: %s", e, exc_info=True)

        fallback_response = await _try_fallback(model_id, req, user_keys)
        if fallback_response:
            return fallback_response

        raise HTTPException(
            status_code=502,
            detail={"error": {"message": str(e), "type": "provider_error"}},
        )


async def _handle_stream(provider, model_name: str, req: ChatCompletionRequest, *, api_key: Optional[str] = None):
    """Return an SSE streaming response."""

    async def generate():
        try:
            async for chunk in provider.chat_completion_stream(
                messages=req.messages,
                model=model_name,
                api_key=api_key,
                temperature=req.temperature or 1.0,
                max_tokens=req.max_tokens,
            ):
                yield chunk
        except Exception as e:
            logger.error("Stream error: %s", e)
            error_chunk = {
                "error": {"message": str(e), "type": "stream_error"},
            }
            yield f"data: {json.dumps(error_chunk)}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


async def _try_fallback(
    failed_model: str,
    req: ChatCompletionRequest,
    user_keys: dict[str, str],
) -> Optional[ChatCompletionResponse]:
    """Attempt fallback to alternate providers using available keys."""
    decision = route(req.messages, budget_cap=req.budget_cap)

    for model_id in decision.fallback_chain:
        if model_id == failed_model:
            continue
        provider_name, model_name = registry.resolve_model(model_id)
        provider = registry.get_provider(model_id)
        if not provider:
            continue
        user_key = user_keys.get(provider_name)
        try:
            response = await provider.chat_completion(
                messages=req.messages,
                model=model_name,
                api_key=user_key,
                temperature=req.temperature or 1.0,
                max_tokens=req.max_tokens,
            )
            logger.info("Fallback to %s succeeded", model_id)
            return response
        except Exception:
            continue

    return None
