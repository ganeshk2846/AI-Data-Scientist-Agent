"""
backend/tests/test_phase4_orchestrator.py
End-to-end integration and API tests for Phase 4 Unified Analytical Orchestrator.
"""

from pathlib import Path
import sqlite3
import pytest
from fastapi.testclient import TestClient

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.main import app
from backend.app.schema.service import SchemaService, schema_service


def test_conversational_follow_up_orchestration(tmp_path: Path):
    """
    Verifies multi-turn conversational intelligence:
    Turn 1: Descriptive query establishes entity and metric context.
    Turn 2: Follow-up question ('Why did it decrease?') inherits entity context without re-prompting.
    """
    db_file = tmp_path / "conv.sqlite"
    conn = sqlite3.connect(str(db_file))
    with conn:
        conn.execute("CREATE TABLE orders (order_id INT, customer_id INT, order_date TEXT, total_amount REAL);")
        for i in range(1, 20):
            conn.execute(f"INSERT INTO orders VALUES ({i}, 10, '2026-01-{i:02d}', {50.0 + i * 10});")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(db_file), name="conv_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    session_id = "test_conv_session_101"

    # Turn 1: Descriptive
    t1 = analytical_orchestrator.analyze(
        question="What were our sales trends by date?",
        session_id=session_id,
        catalog=cat,
    )
    assert t1.success is True
    assert t1.analytical_type == IntentCategory.DESCRIPTIVE

    # Turn 2: Follow-up Diagnostic (inherits 'orders' and 'total_amount')
    t2 = analytical_orchestrator.analyze(
        question="Why did total_amount change between periods?",
        session_id=session_id,
        catalog=cat,
    )
    assert t2.success is True
    assert t2.analytical_type == IntentCategory.DIAGNOSTIC
    assert "orders" in t2.source_tables

    adapter.disconnect()


def test_api_analytics_execute_endpoint():
    """Verifies POST /api/v1/analytics/execute works through FastAPI TestClient."""
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/analytics/execute",
            json={"question": "What is the trend in order amounts over time?"},
        )
        assert res.status_code == 200
        body = res.json()
        assert body["success"] is True
        assert body["data"]["analytical_type"] == "DESCRIPTIVE"
        assert len(body["data"]["findings"]) > 0


def test_api_analytics_classify_endpoint():
    """Verifies POST /api/v1/analytics/classify works through FastAPI TestClient."""
    with TestClient(app) as client:
        res = client.post(
            "/api/v1/analytics/classify",
            json={"question": "Forecast revenue for next quarter"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["primary_intent"] == "PREDICTIVE"
        assert data["complexity"] == "ADVANCED"
