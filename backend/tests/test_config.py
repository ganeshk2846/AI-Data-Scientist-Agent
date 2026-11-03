"""
Tests for application configuration, path resolution, and Groq credential redaction.
"""

from pathlib import Path
from backend.app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.APP_NAME == "AI for BI Data Scientist Agent"
    assert s.APP_VERSION == "0.1.0"
    assert s.SQL_QUERY_TIMEOUT_SECONDS == 30
    assert s.SQL_MAX_ROWS_RETURN == 1000
    assert s.GROQ_MODEL == "openai/gpt-oss-120b"
    assert s.GROQ_BASE_URL == "https://api.groq.com/openai/v1"


def test_resolved_paths():
    s = Settings()
    db_path = s.resolved_ecommerce_db_path
    assert isinstance(db_path, Path)
    assert db_path.name in ["ecommerce.sqlite", "ecommerce.db"]
    assert db_path.exists(), "Database file must exist on disk"


def test_secret_redaction():
    s = Settings(
        GROQ_API_KEY="gsk_real_secret_key_1234567890",
    )
    safe = s.get_safe_dict()
    assert safe["GROQ_API_KEY"] == "[REDACTED]"


def test_groq_configuration_and_readiness():
    # Unconfigured when None
    s_none = Settings(GROQ_API_KEY=None)
    assert s_none.is_llm_configured() is False

    # Unconfigured when placeholder
    s_placeholder = Settings(GROQ_API_KEY="your_groq_api_key_here")
    assert s_placeholder.is_llm_configured() is False

    # Configured when valid key provided
    s_valid = Settings(
        GROQ_API_KEY="gsk_actual_groq_test_key_valid",
        GROQ_MODEL="llama-3.3-70b-versatile",
    )
    assert s_valid.is_llm_configured() is True
    assert s_valid.GROQ_MODEL == "llama-3.3-70b-versatile"
    safe = s_valid.get_safe_dict()
    assert safe["GROQ_API_KEY"] == "[REDACTED]"
    assert safe["llm_configured"] is True
