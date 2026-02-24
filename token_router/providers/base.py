"""Abstract base class for provider adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator, Dict, List, Optional

from token_router.models import ChatCompletionResponse, ChatMessage, Usage


@dataclass
class TokenPricing:
    """Per-million token pricing."""
    input_cost: float   # USD per 1M input tokens
    output_cost: float  # USD per 1M output tokens

    def estimate(self, input_tokens: int, output_tokens: int) -> float:
        return (input_tokens * self.input_cost + output_tokens * self.output_cost) / 1_000_000


@dataclass
class ModelInfo:
    """Model metadata."""
    id: str
    name: str
    provider: str
    max_tokens: int
    pricing: TokenPricing
    quality_tier: int  # 1=highest, 3=lowest


class ProviderAdapter(ABC):
    """Base class all provider adapters must implement.

    API keys are resolved per-request in this priority:
      1. api_key parameter (user's own key from request header)
      2. Server default key (from environment variable)
      3. Error if neither available
    """

    provider_name: str = ""

    @abstractmethod
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
        """Send a chat completion request and return a response."""

    @abstractmethod
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
        """Yield SSE-formatted chunks for streaming responses."""

    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """Return available models for this provider."""

    @abstractmethod
    def get_pricing(self, model: str) -> TokenPricing:
        """Return pricing for a specific model."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider API is reachable."""

    def supports_model(self, model: str) -> bool:
        """Check if this provider handles the given model ID."""
        return any(m.id == model for m in self.list_models())
