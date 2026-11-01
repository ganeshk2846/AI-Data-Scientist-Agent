"""
Application configuration using Pydantic v2 Settings.
Loads environment variables safely, resolves paths robustly, and redacts secrets.
"""

import os
from pathlib import Path
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


# Project root determination (two levels up from backend/app/core)
BACKEND_DIR = Path(__file__).resolve().parent.parent.parent
REPO_ROOT = BACKEND_DIR.parent


class Settings(BaseSettings):
    """Application configuration settings."""

    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application settings
    APP_NAME: str = "AI for BI Data Scientist Agent"
    APP_VERSION: str = "0.1.0"
    APP_ENV: str = Field(default="development", description="development, testing, production")
    APP_DEBUG: bool = Field(default=False)
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8001
    LOG_LEVEL: str = "INFO"

    # CORS settings
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
    ]

    # Database paths
    ECOMMERCE_DB_PATH: str = Field(
        default="ecommerce.sqlite",
        description="Path to read-only business SQLite warehouse",
    )
    APP_DB_PATH: str = Field(
        default="agent_app.sqlite",
        description="Path to writable agent-owned store for checkpoints and traces",
    )

    # LLM Provider Configuration (Optional at startup)
    LLM_PROVIDER: str = Field(
        default="mock",
        description="LLM provider: openai, anthropic, gemini, or mock",
    )
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # Timeouts & safety limits
    SQL_QUERY_TIMEOUT_SECONDS: int = 30
    SQL_MAX_ROWS_RETURN: int = 1000
    LLM_TIMEOUT_SECONDS: int = 45

    @property
    def resolved_ecommerce_db_path(self) -> Path:
        """Resolves the read-only database path relative to REPO_ROOT if relative."""
        p = Path(self.ECOMMERCE_DB_PATH)
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p.resolve()

    @property
    def resolved_app_db_path(self) -> Path:
        """Resolves the writable application store path relative to REPO_ROOT if relative."""
        p = Path(self.APP_DB_PATH)
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p.resolve()

    def is_llm_configured(self) -> bool:
        """Checks if the configured LLM provider has a valid API key."""
        provider = self.LLM_PROVIDER.lower()
        if provider == "openai":
            return bool(self.OPENAI_API_KEY and self.OPENAI_API_KEY.strip() and not self.OPENAI_API_KEY.startswith("your_"))
        elif provider == "anthropic":
            return bool(self.ANTHROPIC_API_KEY and self.ANTHROPIC_API_KEY.strip() and not self.ANTHROPIC_API_KEY.startswith("your_"))
        elif provider == "gemini":
            return bool(self.GEMINI_API_KEY and self.GEMINI_API_KEY.strip() and not self.GEMINI_API_KEY.startswith("your_"))
        elif provider == "mock":
            return True
        return False

    def get_safe_dict(self) -> dict:
        """Returns configuration dictionary with secrets redacted."""
        d = self.model_dump()
        for k in ["OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
            if d.get(k):
                d[k] = "[REDACTED]"
            else:
                d[k] = None
        d["ecommerce_db_exists"] = self.resolved_ecommerce_db_path.exists()
        d["llm_configured"] = self.is_llm_configured()
        return d


settings = Settings()

