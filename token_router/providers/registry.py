"""Extended model registry with all providers and pricing."""

from __future__ import annotations

from typing import Dict, List, Optional

from token_router.providers.base import ModelInfo, ProviderAdapter, TokenPricing

# ── Complete Model Catalog ──────────────────────────────────────

MODELS: Dict[str, ModelInfo] = {
    # OpenAI
    "openai/gpt-4o": ModelInfo(
        id="openai/gpt-4o", name="GPT-4o", provider="openai",
        max_tokens=16384, pricing=TokenPricing(2.50, 10.00), quality_tier=1,
    ),
    "openai/gpt-4o-mini": ModelInfo(
        id="openai/gpt-4o-mini", name="GPT-4o Mini", provider="openai",
        max_tokens=16384, pricing=TokenPricing(0.15, 0.60), quality_tier=2,
    ),
    # Anthropic
    "anthropic/claude-opus": ModelInfo(
        id="anthropic/claude-opus", name="Claude Opus 4", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(15.00, 75.00), quality_tier=1,
    ),
    "anthropic/claude-sonnet": ModelInfo(
        id="anthropic/claude-sonnet", name="Claude Sonnet 4", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(3.00, 15.00), quality_tier=1,
    ),
    "anthropic/claude-haiku": ModelInfo(
        id="anthropic/claude-haiku", name="Claude Haiku 3.5", provider="anthropic",
        max_tokens=8192, pricing=TokenPricing(0.80, 4.00), quality_tier=2,
    ),
    # Groq
    "groq/llama-3.3-70b": ModelInfo(
        id="groq/llama-3.3-70b", name="Llama 3.3 70B", provider="groq",
        max_tokens=8192, pricing=TokenPricing(0.59, 0.79), quality_tier=2,
    ),
    "groq/mixtral-8x7b": ModelInfo(
        id="groq/mixtral-8x7b", name="Mixtral 8x7B", provider="groq",
        max_tokens=32768, pricing=TokenPricing(0.24, 0.24), quality_tier=3,
    ),
    # Google
    "google/gemini-2.5-pro": ModelInfo(
        id="google/gemini-2.5-pro", name="Gemini 2.5 Pro", provider="google",
        max_tokens=8192, pricing=TokenPricing(1.25, 5.00), quality_tier=1,
    ),
    "google/gemini-2.5-flash": ModelInfo(
        id="google/gemini-2.5-flash", name="Gemini 2.5 Flash", provider="google",
        max_tokens=8192, pricing=TokenPricing(0.15, 0.60), quality_tier=2,
    ),
    # DeepSeek
    "deepseek/deepseek-v3": ModelInfo(
        id="deepseek/deepseek-v3", name="DeepSeek V3", provider="deepseek",
        max_tokens=8192, pricing=TokenPricing(0.27, 1.10), quality_tier=2,
    ),
    "deepseek/deepseek-r1": ModelInfo(
        id="deepseek/deepseek-r1", name="DeepSeek R1", provider="deepseek",
        max_tokens=8192, pricing=TokenPricing(0.55, 2.19), quality_tier=1,
    ),
}

# ── Difficulty-based Routing ────────────────────────────────────

DIFFICULTY_ROUTING = {
    "simple": ["groq/llama-3.3-70b", "deepseek/deepseek-v3", "groq/mixtral-8x7b"],
    "medium": ["openai/gpt-4o-mini", "anthropic/claude-haiku", "google/gemini-2.5-flash"],
    "complex": ["openai/gpt-4o", "anthropic/claude-sonnet", "google/gemini-2.5-pro"],
}

FALLBACK_CHAINS = {
    "quality": ["anthropic/claude-sonnet", "openai/gpt-4o", "google/gemini-2.5-pro", "deepseek/deepseek-r1"],
    "balanced": ["openai/gpt-4o-mini", "anthropic/claude-haiku", "groq/llama-3.3-70b", "deepseek/deepseek-v3"],
    "economy": ["groq/mixtral-8x7b", "groq/llama-3.3-70b", "deepseek/deepseek-v3", "google/gemini-2.5-flash"],
}


class ModelRegistry:
    """Registry of all available models across providers."""

    def __init__(self) -> None:
        self._providers: Dict[str, ProviderAdapter] = {}

    def register_provider(self, name: str, adapter: ProviderAdapter) -> None:
        self._providers[name] = adapter

    def get_provider(self, model_id: str) -> Optional[ProviderAdapter]:
        provider_name = model_id.split("/")[0] if "/" in model_id else None
        return self._providers.get(provider_name) if provider_name else None

    def get_model_info(self, model_id: str) -> Optional[ModelInfo]:
        return MODELS.get(model_id)

    def list_all_models(self) -> List[ModelInfo]:
        available = []
        for model in MODELS.values():
            provider = self._providers.get(model.provider)
            if provider:
                available.append(model)
        return available

    def resolve_model(self, model_id: str) -> tuple[str, str]:
        """Parse 'provider/model' into (provider_name, api_model_name)."""
        if "/" in model_id:
            provider, model = model_id.split("/", 1)
            return provider, model
        # Try to find in known models
        for mid, info in MODELS.items():
            if model_id in mid:
                return info.provider, model_id
        return "", model_id

    def get_models_by_difficulty(self, difficulty: str) -> List[str]:
        return DIFFICULTY_ROUTING.get(difficulty, DIFFICULTY_ROUTING["medium"])

    def get_fallback_chain(self, strategy: str = "balanced") -> List[str]:
        return FALLBACK_CHAINS.get(strategy, FALLBACK_CHAINS["balanced"])

    def estimate_cost(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        model = MODELS.get(model_id)
        if not model:
            return 0.0
        return model.pricing.estimate(input_tokens, output_tokens)

    def select_by_budget(self, budget_usd: float, input_tokens: int = 1000, output_tokens: int = 500) -> List[str]:
        """Return models that fit within budget, sorted by quality."""
        affordable = []
        for mid, model in MODELS.items():
            cost = model.pricing.estimate(input_tokens, output_tokens)
            if cost <= budget_usd:
                affordable.append((model.quality_tier, cost, mid))
        affordable.sort()
        return [mid for _, _, mid in affordable]


# Singleton
registry = ModelRegistry()
