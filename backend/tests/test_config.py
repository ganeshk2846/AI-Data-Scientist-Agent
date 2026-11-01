"""
Tests for application configuration, path resolution, and secret redaction.
"""

from pathlib import Path
from backend.app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.APP_NAME == "AI for BI Data Scientist Agent"
    assert s.APP_VERSION == "0.1.0"
    assert s.SQL_QUERY_TIMEOUT_SECONDS == 30
    assert s.SQL_MAX_ROWS_RETURN == 1000


def test_resolved_paths():
    s = Settings()
    db_path = s.resolved_ecommerce_db_path
    assert isinstance(db_path, Path)
    assert db_path.name == "ecommerce.sqlite"
    assert db_path.exists(), "ecommerce.sqlite must exist on disk"


def test_secret_redaction():
    s = Settings(
        OPENAI_API_KEY="sk-test-secret-key-1234567890",
        ANTHROPIC_API_KEY="test-anthropic-key",
    )
    safe = s.get_safe_dict()
    assert safe["OPENAI_API_KEY"] == "[REDACTED]"
    assert safe["ANTHROPIC_API_KEY"] == "[REDACTED]"
    assert safe["GEMINI_API_KEY"] in [None, "[REDACTED]"]


def test_gemini_configuration_and_redaction():
    s = Settings(
        LLM_PROVIDER="gemini",
        GEMINI_API_KEY="AIzaSyTestGeminiKey123",
        GEMINI_MODEL="gemini-3.5-flash-lite",
    )
    assert s.is_llm_configured() is True
    assert s.GEMINI_MODEL == "gemini-3.5-flash-lite"
    safe = s.get_safe_dict()
    assert safe["GEMINI_API_KEY"] == "[REDACTED]"
    assert safe["llm_configured"] is True


