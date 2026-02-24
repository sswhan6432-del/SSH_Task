"""Pydantic models for OpenAI-compatible API."""

from __future__ import annotations

import time
import uuid
from typing import Any, List, Literal, Optional, Union

from pydantic import BaseModel, Field


# ── Request Models ──────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str
    content: Union[str, list]
    name: Optional[str] = None


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    max_tokens: Optional[int] = None
    stream: Optional[bool] = False
    top_p: Optional[float] = 1.0
    frequency_penalty: Optional[float] = 0.0
    presence_penalty: Optional[float] = 0.0
    stop: Optional[Union[str, List[str]]] = None
    n: Optional[int] = 1

    # TokenRouter extensions
    budget_cap: Optional[float] = None  # Max cost in USD
    auto_route: Optional[bool] = False  # Use smart routing


# ── Response Models ─────────────────────────────────────────────

class Usage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class Choice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: Optional[str] = "stop"


class ChatCompletionResponse(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[Choice]
    usage: Usage

    # TokenRouter extensions
    cost_usd: Optional[float] = None
    provider: Optional[str] = None


# ── Streaming Models ────────────────────────────────────────────

class DeltaMessage(BaseModel):
    role: Optional[str] = None
    content: Optional[str] = None


class StreamChoice(BaseModel):
    index: int = 0
    delta: DeltaMessage
    finish_reason: Optional[str] = None


class ChatCompletionChunk(BaseModel):
    id: str = Field(default_factory=lambda: f"chatcmpl-{uuid.uuid4().hex[:12]}")
    object: Literal["chat.completion.chunk"] = "chat.completion.chunk"
    created: int = Field(default_factory=lambda: int(time.time()))
    model: str
    choices: List[StreamChoice]


# ── Optimize Endpoint Models ────────────────────────────────────

class OptimizeRequest(BaseModel):
    text: str
    level: int = 2  # 1=mild, 2=balanced, 3=aggressive


class OptimizeResponse(BaseModel):
    original_tokens: int
    compressed_tokens: int
    reduction_rate: float
    compressed_text: str
    level: int


# ── Route Endpoint Models ──────────────────────────────────────

class RouteRequest(BaseModel):
    messages: List[ChatMessage]
    budget_cap: Optional[float] = None
    prefer: Optional[str] = None  # "speed", "quality", "cost"


class ModelRecommendation(BaseModel):
    model: str
    provider: str
    reason: str
    estimated_cost: float
    quality_tier: int


class RouteResponse(BaseModel):
    intent: str
    confidence: float
    difficulty: str  # "simple", "medium", "complex"
    recommendations: List[ModelRecommendation]
    fallback_chain: List[str]


# ── Stats Models ───────────────────────────────────────────────

class StatsResponse(BaseModel):
    total_requests: int = 0
    total_tokens: int = 0
    total_cost_usd: float = 0.0
    total_savings_usd: float = 0.0
    cache_hit_rate: float = 0.0
    requests_by_provider: dict = Field(default_factory=dict)
    requests_by_model: dict = Field(default_factory=dict)
    avg_latency_ms: float = 0.0


# ── Error Models ───────────────────────────────────────────────

class ErrorDetail(BaseModel):
    message: str
    type: str = "api_error"
    code: Optional[str] = None


class ErrorResponse(BaseModel):
    error: ErrorDetail


# ── Auth Models ───────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str
    display_name: Optional[str] = ""


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


class UserProfile(BaseModel):
    id: str
    email: str
    display_name: str
    api_key: str
    created_at: float


# ── Provider Key Models ──────────────────────────────────────

class ProviderKeyRequest(BaseModel):
    encrypted_key: str  # AES-256-GCM encrypted blob (base64)
    label: Optional[str] = ""


class ProviderKeyResponse(BaseModel):
    id: str
    provider: str
    encrypted_key: str  # Encrypted blob (server cannot decrypt)
    label: str
    created_at: float
    updated_at: float


class ProviderKeysListResponse(BaseModel):
    keys: List[ProviderKeyResponse]
