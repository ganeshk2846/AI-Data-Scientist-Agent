"""
backend/tests/test_vertical_slice.py
Phase 2: Early Working Vertical Slice Test Suite (Ollama qwen3:4b + ecommerce.db).
Verifies:
1. Live local Ollama qwen3:4b provider integration (Strict No-Mocking Policy).
2. Dynamic schema profiling and active database grounding on ecommerce.db (46 tables, ~2.4M rows).
3. End-to-end question answering pipeline with real AST validation and read-only execution.
4. Column hallucination detection and rejection via SQLValidator.
5. Strict bounded 1-retry repair loop enforcement.
6. Absolute bitwise immutability of ecommerce.db (SHA-256 invariance).
"""

import asyncio
import hashlib
import os
from pathlib import Path
import pytest
from backend.app.core.config import settings
from backend.app.core.contracts import SupportedEngine
from backend.app.db.manager import db_manager
from backend.app.llm.client import get_llm_provider
from backend.app.llm.ollama_client import OllamaLLMProvider
from backend.app.schema.service import schema_service
from backend.app.sql.repair import sql_repair_loop
from backend.app.sql.validator import sql_validator
from backend.app.workflow.orchestrator import multi_agent_orchestrator

EXPECTED_ECOMMERCE_SHA256 = "366080c92e8dc7024a15b95730a35e63ac16765f748142f51cc40f92b63f3d9e"


@pytest.fixture(autouse=True)
def configure_ollama_environment():
    """Enforces live Ollama provider for all vertical slice tests (Strict No-Mocking Policy)."""
    prev_provider = settings.LLM_PROVIDER
    settings.LLM_PROVIDER = "ollama"
    os.environ["LLM_PROVIDER"] = "ollama"
    yield
    settings.LLM_PROVIDER = prev_provider


def compute_file_sha256(file_path: Path) -> str:
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def test_ollama_provider_configuration():
    """Verifies that the LLM provider is the real OllamaLLMProvider targeting qwen3:4b."""
    provider = get_llm_provider()
    assert isinstance(provider, OllamaLLMProvider), f"Expected OllamaLLMProvider, got {type(provider)}"
    assert provider.model == "qwen3:4b"
    assert "11434" in provider.base_url
    assert settings.LLM_PROVIDER == "ollama"


def test_active_database_profiling_and_grounding():
    """Verifies active database is ecommerce.db and catalog has 46 tables and ~2.4M rows."""
    adapter = db_manager.get_active_adapter()
    assert adapter.engine_type == SupportedEngine.SQLITE

    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    assert catalog is not None
    assert catalog.total_tables == 46
    assert catalog.total_rows > 2_000_000
    assert "orders" in catalog.tables
    assert "customers" in catalog.tables
    assert "order_items" in catalog.tables
    assert "products" in catalog.tables
    assert "product_categories" in catalog.tables


def test_column_hallucination_detection_and_rejection():
    """Verifies that SQLValidator detects and rejects non-existent hallucinated columns."""
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    hallucinated_sql = "SELECT non_existent_column_xyz, order_id FROM orders"
    is_valid, sanitized, errors = sql_validator.validate_and_format_sql(hallucinated_sql, catalog, dialect="sqlite")
    assert not is_valid
    assert any("non_existent_column_xyz" in err for err in errors)


def test_bounded_repair_loop_enforcement():
    """Verifies that sql_repair_loop strictly rejects repair attempts beyond 1 retry."""
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    with pytest.raises(ValueError, match="strictly 1 repair retry permitted"):
        asyncio.run(
            sql_repair_loop.attempt_repair(
                query="What are total sales?",
                failing_sql="SELECT fake_col FROM orders",
                error_message="Column fake_col does not exist",
                schema_context="Table: orders",
                catalog=catalog,
                attempt_number=2,
            )
        )


def test_end_to_end_total_sales_and_orders():
    """E2E Test 1: Total sales and order count with real Ollama qwen3:4b and ecommerce.db."""
    query = "What are the total sales and order count?"
    result = asyncio.run(multi_agent_orchestrator.run(query))

    assert result.sanitized_sql is not None
    assert "orders" in result.sanitized_sql.lower()
    assert result.query_result is not None
    assert result.query_result.row_count >= 1
    first_row = result.query_result.rows[0]
    # Check that order count is 150000
    order_cnt_val = next(v for k, v in first_row.items() if "count" in k.lower() or "order" in k.lower())
    assert int(order_cnt_val) == 150000
    assert len(result.composed_answer) > 50


def test_end_to_end_annual_sales_trends():
    """E2E Test 2: Annual sales trends by year."""
    query = "What are the total sales by year?"
    result = asyncio.run(multi_agent_orchestrator.run(query))

    assert result.sanitized_sql is not None
    assert "orders" in result.sanitized_sql.lower() or "sales" in result.sanitized_sql.lower()
    assert result.query_result is not None
    assert result.query_result.row_count >= 1
    assert len(result.composed_answer) > 50


def test_end_to_end_top_customers_by_spend():
    """E2E Test 3: Top customers by total spend."""
    query = "Who are the top 5 customers by total order spend?"
    result = asyncio.run(multi_agent_orchestrator.run(query))

    assert result.sanitized_sql is not None
    assert result.query_result is not None
    assert 1 <= result.query_result.row_count <= 5
    assert len(result.composed_answer) > 50


def test_ecommerce_db_sha256_invariance():
    """Verifies that ecommerce.db remains strictly bitwise identical after all test queries."""
    db_path = settings.resolved_ecommerce_db_path
    current_sha = compute_file_sha256(db_path)
    assert current_sha == EXPECTED_ECOMMERCE_SHA256, (
        f"CRITICAL: ecommerce.db SHA-256 hash changed! Expected {EXPECTED_ECOMMERCE_SHA256}, got {current_sha}"
    )
