"""Smart Router - Intent-based model selection and cost optimization."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import List, Optional

from token_router.models import ChatMessage, ModelRecommendation, RouteResponse
from token_router.providers.registry import MODELS, registry

logger = logging.getLogger(__name__)

# Intent-to-difficulty mapping
INTENT_DIFFICULTY = {
    "research": "complex",
    "analyze": "complex",
    "implement": "medium",
}

# Keyword-based difficulty detection (fallback)
SIMPLE_KEYWORDS = {
    "translate", "summarize", "summary", "explain", "define", "what is",
    "hello", "hi", "hey", "thanks", "help", "faq", "list", "how to",
}
COMPLEX_KEYWORDS = {
    "architecture", "design", "optimize", "refactor", "debug", "security",
    "implement complex", "multi-step", "reasoning", "prove", "analyze deeply",
    "compare and contrast", "trade-off", "system design",
}


@dataclass
class RoutingDecision:
    difficulty: str
    intent: str
    confidence: float
    recommended_models: List[str]
    fallback_chain: List[str]


def _classify_difficulty(text: str) -> str:
    """Simple keyword-based difficulty classification."""
    lower = text.lower()
    for kw in COMPLEX_KEYWORDS:
        if kw in lower:
            return "complex"
    for kw in SIMPLE_KEYWORDS:
        if kw in lower:
            return "simple"
    return "medium"


def _extract_user_text(messages: List[ChatMessage]) -> str:
    """Extract the last user message for intent analysis."""
    for msg in reversed(messages):
        if msg.role == "user":
            return msg.content if isinstance(msg.content, str) else str(msg.content)
    return ""


def route(
    messages: List[ChatMessage],
    *,
    budget_cap: Optional[float] = None,
    prefer: Optional[str] = None,
) -> RoutingDecision:
    """Determine optimal model based on intent and constraints.

    Uses NLP intent detection if available, falls back to keyword analysis.
    """
    user_text = _extract_user_text(messages)
    intent = "implement"
    confidence = 0.5

    # Try NLP intent detection (from existing SSH_WEB module)
    try:
        from nlp.intent_detector import detect_intent
        analysis = detect_intent(user_text)
        intent = analysis.intent
        confidence = analysis.confidence
    except Exception as e:
        logger.debug("NLP intent detection unavailable: %s", e)

    # Determine difficulty
    difficulty = INTENT_DIFFICULTY.get(intent, "medium")
    if confidence < 0.6:
        # Low confidence: fall back to keyword analysis
        difficulty = _classify_difficulty(user_text)

    # Get candidate models
    candidates = registry.get_models_by_difficulty(difficulty)

    # Apply budget constraint
    if budget_cap is not None:
        affordable = registry.select_by_budget(budget_cap)
        candidates = [m for m in candidates if m in affordable] or affordable[:3]

    # Apply preference
    if prefer == "speed":
        # Prefer Groq (fastest inference)
        candidates.sort(key=lambda m: 0 if "groq" in m else 1)
    elif prefer == "quality":
        candidates.sort(key=lambda m: MODELS[m].quality_tier if m in MODELS else 9)
    elif prefer == "cost":
        candidates.sort(key=lambda m: MODELS[m].pricing.estimate(1000, 500) if m in MODELS else 999)

    # Build fallback chain
    if prefer in ("quality", None):
        fallback = registry.get_fallback_chain("quality" if difficulty == "complex" else "balanced")
    else:
        fallback = registry.get_fallback_chain("economy")

    return RoutingDecision(
        difficulty=difficulty,
        intent=intent,
        confidence=confidence,
        recommended_models=candidates,
        fallback_chain=fallback,
    )


def build_route_response(decision: RoutingDecision) -> RouteResponse:
    """Convert internal routing decision to API response."""
    recommendations = []
    for model_id in decision.recommended_models[:3]:
        info = MODELS.get(model_id)
        if not info:
            continue
        recommendations.append(ModelRecommendation(
            model=model_id,
            provider=info.provider,
            reason=_recommendation_reason(decision.difficulty, info),
            estimated_cost=info.pricing.estimate(1000, 500),
            quality_tier=info.quality_tier,
        ))

    return RouteResponse(
        intent=decision.intent,
        confidence=decision.confidence,
        difficulty=decision.difficulty,
        recommendations=recommendations,
        fallback_chain=decision.fallback_chain,
    )


def _recommendation_reason(difficulty: str, info) -> str:
    reasons = {
        "simple": f"Fast and cost-effective for simple tasks (${info.pricing.estimate(1000, 500)*1000:.2f}/1K req)",
        "medium": f"Balanced quality/cost for standard tasks (tier {info.quality_tier})",
        "complex": f"High quality for complex reasoning (tier {info.quality_tier})",
    }
    return reasons.get(difficulty, "General purpose model")
