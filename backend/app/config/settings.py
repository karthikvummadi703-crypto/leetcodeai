"""
Configuration module — loads and validates all environment variables.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Determine the base directory of the backend package.
BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/

# Load the .env file that sits next to main.py.
load_dotenv(BASE_DIR / ".env")


class Settings(BaseSettings):
    """Validated application settings sourced from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- OpenRouter ---
    openrouter_api_key: str = Field(default="", description="OpenRouter API key")
    openrouter_model: str = Field(
        default="google/gemini-2.5-flash",
        description="Default model identifier on OpenRouter",
    )

    # --- Firebase ---
    firebase_project_id: str = Field(default="", description="Firebase project ID")
    firebase_client_email: str = Field(default="", description="Firebase service-account email")
    firebase_private_key: str = Field(
        default="", description="Firebase service-account private key (PEM)"
    )

    # --- App ---
    app_env: str = Field(default="development", description="development | staging | production")
    log_level: str = Field(default="DEBUG", description="Loguru log level")
    backend_url: str = Field(default="http://localhost:8000")
    frontend_url: str = Field(
        default="http://localhost:5173",
        description="CORS origin(s); comma-separated for multiple (e.g. Firebase Hosting .web.app + .firebaseapp.com)",
    )

    # --- Rate limiting ---
    rate_limit_enabled: bool = Field(default=True, description="Enable per-user rate limiting")
    rate_limit_max_requests: int = Field(default=20, description="Max requests per window per user")
    rate_limit_window_seconds: float = Field(
        default=60.0, description="Rate-limit window length (seconds)"
    )

    # --- RAG / vector search (ChromaDB, embedded) ---
    rag_vector_enabled: bool = Field(
        default=True,
        description="Enable ChromaDB semantic retrieval for the RAG pipeline",
    )

    # --- LeetCode account integration ---
    leetcode_cache_ttl_seconds: float = Field(
        default=300.0, description="How long to cache a user's LeetCode account data"
    )

    # --- Derived helpers ---
    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def allowed_origins(self) -> list[str]:
        """Origins permitted for CORS."""
        if not self.is_production:
            return ["*"]
        # FRONTEND_URL may list several origins (Firebase Hosting exposes
        # <project>.web.app and <project>.firebaseapp.com) separated by commas.
        origins = [origin.strip() for origin in self.frontend_url.split(",") if origin.strip()]
        return origins or ["*"]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the singleton Settings instance (cached)."""
    return Settings()
