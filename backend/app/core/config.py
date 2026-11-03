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
    APP_SECRET_KEY: str = Field(
        default="ai-for-bi-secret-key-32b-change-in-production",
        description="Secret key for symmetric credential encryption",
    )

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
        default="ecommerce.db",
        description="Path to read-only business SQLite warehouse",
    )
    APP_DB_PATH: str = Field(
        default="agent_app.sqlite",
        description="Path to writable agent-owned store for checkpoints and traces",
    )
    LANCEDB_DIR: str = Field(
        default="data/lancedb",
        description="Path to persistent LanceDB vector store directory",
    )
    BM25_DIR: str = Field(
        default="data/bm25",
        description="Path to persistent BM25 index directory",
    )
    EMBEDDING_MODEL_NAME: str = Field(
        default="BAAI/bge-small-en-v1.5",
        description="FastEmbed ONNX local embedding model identifier",
    )

    # LLM Configuration (Groq is the single supported LLM provider)
    GROQ_API_KEY: Optional[str] = Field(
        default=None,
        description="Groq API key for single-provider LLM inference",
    )
    GROQ_MODEL: str = Field(
        default="openai/gpt-oss-120b",
        description="Configured Groq model identifier",
    )
    GROQ_BASE_URL: str = Field(
        default="https://api.groq.com/openai/v1",
        description="Groq OpenAI-compatible Chat Completions API base URL",
    )

    # Timeouts & safety limits
    SQL_QUERY_TIMEOUT_SECONDS: int = 30
    SQL_MAX_ROWS_RETURN: int = 1000
    LLM_TIMEOUT_SECONDS: int = 120

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

    @property
    def resolved_lancedb_dir(self) -> Path:
        """Resolves the LanceDB directory path relative to REPO_ROOT."""
        p = Path(self.LANCEDB_DIR)
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p.resolve()

    @property
    def resolved_bm25_dir(self) -> Path:
        """Resolves the BM25 index directory path relative to REPO_ROOT."""
        p = Path(self.BM25_DIR)
        if not p.is_absolute():
            p = REPO_ROOT / p
        return p.resolve()

    def is_llm_configured(self) -> bool:
        """Checks if the Groq LLM provider has a valid API key configured."""
        if not self.GROQ_API_KEY:
            return False
        key = self.GROQ_API_KEY.strip()
        return bool(key and not key.startswith("your_") and key != "gsk_test_placeholder")

    def get_safe_dict(self) -> dict:
        """Returns configuration dictionary with secrets redacted."""
        d = self.model_dump()
        if d.get("GROQ_API_KEY"):
            d["GROQ_API_KEY"] = "[REDACTED]"
        else:
            d["GROQ_API_KEY"] = None
        d["ecommerce_db_exists"] = self.resolved_ecommerce_db_path.exists()
        d["llm_configured"] = self.is_llm_configured()
        return d


settings = Settings()

