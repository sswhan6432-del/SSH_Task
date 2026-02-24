"""TokenRouter - Multi-Model AI Token Optimization Service.

Usage:
    uvicorn token_router.main:app --reload --port 8000

BYOK (Bring Your Own Key):
    Users pass their own AI provider API keys via request headers:
      X-OpenAI-Key: sk-...
      X-Anthropic-Key: sk-ant-...
      X-Groq-Key: gsk-...
      X-Google-Key: ...
      X-DeepSeek-Key: sk-...

    If no user key is provided, server defaults from env vars are used.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from token_router.config import settings
from token_router.providers.registry import registry

logger = logging.getLogger("token_router")

# Header name -> provider name mapping
PROVIDER_KEY_HEADERS = {
    "x-openai-key": "openai",
    "x-anthropic-key": "anthropic",
    "x-groq-key": "groq",
    "x-google-key": "google",
    "x-deepseek-key": "deepseek",
}


# ── Provider Registration ───────────────────────────────────────

def _register_providers() -> None:
    """Register ALL providers unconditionally.

    API keys are resolved per-request:
      1. User's key from X-{Provider}-Key header
      2. Server default from env var
      3. Error if neither
    """
    from token_router.providers.groq_adapter import GroqAdapter
    from token_router.providers.openai_adapter import OpenAIAdapter
    from token_router.providers.anthropic_adapter import AnthropicAdapter
    from token_router.providers.google_adapter import GoogleAdapter
    from token_router.providers.deepseek_adapter import DeepSeekAdapter

    registry.register_provider("groq", GroqAdapter())
    registry.register_provider("openai", OpenAIAdapter())
    registry.register_provider("anthropic", AnthropicAdapter())
    registry.register_provider("google", GoogleAdapter())
    registry.register_provider("deepseek", DeepSeekAdapter())

    # Log which providers have server-default keys
    for name, has_key in [
        ("groq", bool(settings.groq_api_key)),
        ("openai", bool(settings.openai_api_key)),
        ("anthropic", bool(settings.anthropic_api_key)),
        ("google", bool(settings.google_api_key)),
        ("deepseek", bool(settings.deepseek_api_key)),
    ]:
        status = "server-key" if has_key else "BYOK-only"
        logger.info("Provider %s: %s", name, status)


# ── Lifespan ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    _register_providers()
    logger.info("TokenRouter started - 5 providers, 11 models (BYOK enabled)")
    yield
    from token_router import stats_store
    stats_store.force_flush()
    logger.info("TokenRouter shutting down (stats saved)")


# ── App ─────────────────────────────────────────────────────────

app = FastAPI(
    title="TokenRouter",
    description="Multi-Model AI Token Optimization Service with BYOK",
    version="1.1.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Rate limiting
limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    return JSONResponse(
        status_code=429,
        content={"error": {"message": "Rate limit exceeded", "type": "rate_limit_error"}},
    )


# ── API Key Authentication Middleware ───────────────────────────

@app.middleware("http")
async def authenticate(request: Request, call_next):
    path = request.url.path
    if path in ("/health", "/docs", "/openapi.json", "/redoc") or path.startswith("/dashboard"):
        return await call_next(request)

    # If no TokenRouter API keys configured, allow all (dev mode)
    if not settings.api_keys:
        return await call_next(request)

    auth = request.headers.get("authorization", "")
    api_key = request.headers.get("x-api-key", "")

    token = ""
    if auth.startswith("Bearer "):
        token = auth[7:]
    elif api_key:
        token = api_key

    if token not in settings.api_keys:
        return JSONResponse(
            status_code=401,
            content={"error": {"message": "Invalid API key", "type": "authentication_error"}},
        )

    return await call_next(request)


# ── User Provider Key Extraction ────────────────────────────────

def extract_user_provider_keys(request: Request) -> dict[str, str]:
    """Extract per-provider API keys from request headers.

    Headers:
      X-OpenAI-Key: sk-...
      X-Anthropic-Key: sk-ant-...
      X-Groq-Key: gsk-...
      X-Google-Key: ...
      X-DeepSeek-Key: sk-...
    """
    keys = {}
    for header, provider in PROVIDER_KEY_HEADERS.items():
        value = request.headers.get(header, "")
        if value:
            keys[provider] = value
    return keys


# ── Routes ──────────────────────────────────────────────────────

from token_router.endpoints.chat import router as chat_router
from token_router.endpoints.optimize import router as optimize_router
from token_router.endpoints.route import router as route_router
from token_router.endpoints.stats import router as stats_router

app.include_router(chat_router, tags=["Chat"])
app.include_router(optimize_router, tags=["Optimize"])
app.include_router(route_router, tags=["Route"])
app.include_router(stats_router, tags=["Stats"])


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "ok",
        "version": "1.1.0",
        "providers": ["openai", "anthropic", "groq", "google", "deepseek"],
        "models_available": 11,
        "auth_mode": "BYOK (Bring Your Own Key)",
        "key_headers": list(PROVIDER_KEY_HEADERS.keys()),
    }


@app.get("/v1/models")
async def list_models():
    """List all supported models (OpenAI-compatible)."""
    models = registry.list_all_models()
    return {
        "object": "list",
        "data": [
            {
                "id": m.id,
                "object": "model",
                "created": 0,
                "owned_by": m.provider,
                "pricing": {
                    "input_per_1m": m.pricing.input_cost,
                    "output_per_1m": m.pricing.output_cost,
                },
                "quality_tier": m.quality_tier,
            }
            for m in models
        ],
    }


# ── Logging Setup ───────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
