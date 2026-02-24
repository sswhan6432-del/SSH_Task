"""Configuration management via environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    """Application settings loaded from environment variables."""

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = False

    # TokenRouter API keys (comma-separated for multiple keys)
    api_keys: tuple[str, ...] = ()

    # Rate limiting
    rate_limit: str = "60/minute"

    # Provider API keys
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    groq_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""

    # Timeouts (seconds)
    request_timeout: float = 30.0
    stream_timeout: float = 120.0

    # Auth / JWT
    jwt_secret: str = "change-me-in-production"
    jwt_expiry_hours: int = 24
    db_path: str = ""  # defaults to token_router/users.db

    @classmethod
    def from_env(cls) -> Settings:
        raw_keys = os.getenv("TOKENROUTER_API_KEYS", "")
        api_keys = tuple(k.strip() for k in raw_keys.split(",") if k.strip())

        default_db = os.path.join(os.path.dirname(__file__), "users.db")
        return cls(
            host=os.getenv("TOKENROUTER_HOST", "0.0.0.0"),
            port=int(os.getenv("TOKENROUTER_PORT", "8000")),
            debug=os.getenv("TOKENROUTER_DEBUG", "").lower() in ("1", "true"),
            api_keys=api_keys,
            rate_limit=os.getenv("TOKENROUTER_RATE_LIMIT", "60/minute"),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            groq_api_key=os.getenv("GROQ_API_KEY", ""),
            google_api_key=os.getenv("GOOGLE_API_KEY", ""),
            deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", ""),
            request_timeout=float(os.getenv("TOKENROUTER_TIMEOUT", "30")),
            stream_timeout=float(os.getenv("TOKENROUTER_STREAM_TIMEOUT", "120")),
            jwt_secret=os.getenv("TOKENROUTER_JWT_SECRET", "change-me-in-production"),
            jwt_expiry_hours=int(os.getenv("TOKENROUTER_JWT_EXPIRY_HOURS", "24")),
            db_path=os.getenv("TOKENROUTER_DB_PATH", default_db),
        )


# Singleton
settings = Settings.from_env()
