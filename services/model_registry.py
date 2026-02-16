"""Multi-model registry with real pricing and cost-optimized selection.

Pricing as of 2025 per 1M tokens.
"""

from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class ModelConfig:
    id: str
    name: str
    provider: str
    input_cost: float   # $ per 1M input tokens
    output_cost: float  # $ per 1M output tokens
    max_tokens: int
    latency_ms: int     # avg latency estimate
    quality_tier: int   # 1=highest, 3=lowest
    available: bool = True

    def cost_estimate(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost in dollars."""
        return (input_tokens * self.input_cost + output_tokens * self.output_cost) / 1_000_000

    def to_dict(self) -> dict:
        return asdict(self)


# Real pricing data
MODELS = {
    "claude-opus": ModelConfig(
        id="claude-opus",
        name="Claude Opus 4",
        provider="Anthropic",
        input_cost=15.0,
        output_cost=75.0,
        max_tokens=200000,
        latency_ms=3000,
        quality_tier=1,
    ),
    "claude-sonnet": ModelConfig(
        id="claude-sonnet",
        name="Claude Sonnet 4.5",
        provider="Anthropic",
        input_cost=3.0,
        output_cost=15.0,
        max_tokens=200000,
        latency_ms=1500,
        quality_tier=2,
    ),
    "claude-haiku": ModelConfig(
        id="claude-haiku",
        name="Claude Haiku 4.5",
        provider="Anthropic",
        input_cost=0.80,
        output_cost=4.0,
        max_tokens=200000,
        latency_ms=800,
        quality_tier=3,
    ),
    "groq-llama": ModelConfig(
        id="groq-llama",
        name="Llama 3.3 70B (Groq)",
        provider="Groq",
        input_cost=0.59,
        output_cost=0.79,
        max_tokens=131072,
        latency_ms=200,
        quality_tier=3,
    ),
    "groq-mixtral": ModelConfig(
        id="groq-mixtral",
        name="Mixtral 8x7B (Groq)",
        provider="Groq",
        input_cost=0.24,
        output_cost=0.24,
        max_tokens=32768,
        latency_ms=150,
        quality_tier=3,
    ),
    "gpt-4o": ModelConfig(
        id="gpt-4o",
        name="GPT-4o",
        provider="OpenAI",
        input_cost=2.50,
        output_cost=10.0,
        max_tokens=128000,
        latency_ms=2000,
        quality_tier=2,
    ),
    "gpt-4o-mini": ModelConfig(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        provider="OpenAI",
        input_cost=0.15,
        output_cost=0.60,
        max_tokens=128000,
        latency_ms=800,
        quality_tier=3,
    ),
}

# Fallback chain: try higher quality first, fall back to cheaper
FALLBACK_CHAINS = {
    "quality": ["claude-opus", "claude-sonnet", "gpt-4o", "claude-haiku"],
    "balanced": ["claude-sonnet", "gpt-4o", "claude-haiku", "groq-llama"],
    "economy": ["groq-llama", "groq-mixtral", "gpt-4o-mini", "claude-haiku"],
}


class ModelRegistry:
    """Registry for available models with cost-optimized selection."""

    def __init__(self):
        self._models = dict(MODELS)

    def get(self, model_id: str) -> Optional[ModelConfig]:
        return self._models.get(model_id)

    def list_all(self) -> list[dict]:
        return [m.to_dict() for m in self._models.values()]

    def select_by_budget(self, max_cost_per_1k: float, input_tokens: int = 1000, output_tokens: int = 500) -> Optional[ModelConfig]:
        """Select cheapest model that fits budget constraint (cost per 1K tokens)."""
        candidates = []
        for m in self._models.values():
            if not m.available:
                continue
            cost = m.cost_estimate(input_tokens, output_tokens)
            cost_per_1k = cost / ((input_tokens + output_tokens) / 1000)
            if cost_per_1k <= max_cost_per_1k:
                candidates.append((cost_per_1k, m))
        if not candidates:
            return None
        candidates.sort(key=lambda x: (x[1].quality_tier, x[0]))
        return candidates[0][1]

    def get_fallback_chain(self, strategy: str = "balanced") -> list[ModelConfig]:
        chain_ids = FALLBACK_CHAINS.get(strategy, FALLBACK_CHAINS["balanced"])
        return [self._models[mid] for mid in chain_ids if mid in self._models and self._models[mid].available]

    def cost_estimate(self, model_id: str, input_tokens: int, output_tokens: int) -> float:
        model = self._models.get(model_id)
        if not model:
            return 0.0
        return model.cost_estimate(input_tokens, output_tokens)


# Singleton
model_registry = ModelRegistry()
