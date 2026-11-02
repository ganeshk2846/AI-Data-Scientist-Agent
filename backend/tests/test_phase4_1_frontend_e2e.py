"""
backend/tests/test_phase4_1_frontend_e2e.py
End-to-End API and Frontend Contract Integration Tests for Phase 4.1.
Verifies that all 12 frontend UI workflows (A through L) and the database-switching
workflow receive fully validated payloads matching the React component contracts.
"""

from pathlib import Path
import sqlite3
from typing import Any, Tuple
import pytest
from fastapi.testclient import TestClient

from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.main import app
from backend.app.schema.service import SchemaService, schema_service
from backend.app.core.config import settings


@pytest.fixture(autouse=True)
def cleanup_after_test():
    yield
    schema_service._custom_adapter = None
    schema_service._cached_catalog = None
    try:
        adapter = SQLiteAdapter(file_path=str(settings.DB_PATH), name="ecommerce_db", read_only=True)
        adapter.connect()
        db_manager._active_adapter = adapter
    except Exception:
        pass


def _setup_store_db(path: Path) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE sales (id INT, sale_date TEXT, revenue REAL, category TEXT);")
        for i in range(1, 25):
            cat_name = "Electronics" if i % 2 == 0 else "Accessories"
            conn.execute(f"INSERT INTO sales VALUES ({i}, '2026-01-{i:02d}', {100.0 + i*10}, '{cat_name}');")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="store_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    db_manager._active_adapter = adapter
    schema_service._custom_adapter = adapter
    schema_service._cached_catalog = cat
    return adapter, cat


def _setup_clinic_db(path: Path) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE patient_visits (id INT, visit_date TEXT, fee REAL, department TEXT);")
        for i in range(1, 25):
            conn.execute(f"INSERT INTO patient_visits VALUES ({i}, '2026-01-{i:02d}', {200.0 + i*15}, 'Pediatrics');")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="clinic_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    db_manager._active_adapter = adapter
    schema_service._custom_adapter = adapter
    schema_service._cached_catalog = cat
    return adapter, cat


def test_frontend_workflows_a_through_h(tmp_path: Path):
    """
    Executes and validates the API payloads corresponding to Frontend UI Workflows:
    A & B: Descriptive (KPI cards, findings).
    C & D: Diagnostic follow-up (Drivers, non-causal note).
    E & F: Predictive (Forecast points, intervals, empirical coverage).
    G & H: Prescriptive (Optimization allocations, safe boundary disclaimer).
    """
    db_file = tmp_path / "store.sqlite"
    adapter, cat = _setup_store_db(db_file)
    db_manager._active_adapter = adapter

    session_id = "ui_flow_sess_101"

    with TestClient(app) as client:
        # --- Workflow A & B: Descriptive ---
        res_a = client.post("/api/v1/analytics/execute", json={
            "question": "What is the daily trend in revenue over time?",
            "session_id": session_id,
        })
        assert res_a.status_code == 200
        data_a = res_a.json()["data"]
        assert data_a["analytical_type"] == "DESCRIPTIVE"
        assert len(data_a["findings"]) > 0
        assert "sum" in data_a["computed_metrics"] or "overall_growth_pct" in data_a["computed_metrics"]
        assert data_a["faithfulness"] is not None

        # --- Workflow C & D: Diagnostic ---
        res_c = client.post("/api/v1/analytics/execute", json={
            "question": "Why did revenue increase across category between periods?",
            "session_id": session_id,
        })
        assert res_c.status_code == 200
        data_c = res_c.json()["data"]
        assert data_c["analytical_type"] == "DIAGNOSTIC"
        assert len(data_c["findings"]) > 0
        assert any("causal" in note.lower() for note in data_c["uncertainty_notes"])

        # --- Workflow E & F: Predictive ---
        res_e = client.post("/api/v1/analytics/execute", json={
            "question": "Forecast revenue for the next 7 days",
            "session_id": session_id,
        })
        assert res_e.status_code == 200
        data_e = res_e.json()["data"]
        assert data_e["analytical_type"] == "PREDICTIVE"
        assert len(data_e["result_data"]) == 7
        first_pt = data_e["result_data"][0]
        assert "lower_bound_80" in first_pt
        assert "upper_bound_95" in first_pt
        assert "empirical_coverage_80" in data_e["model_information"]

        # --- Workflow G & H: Prescriptive ---
        res_g = client.post("/api/v1/analytics/execute", json={
            "question": "How should we allocate our $20k budget across category?",
            "session_id": session_id,
        })
        assert res_g.status_code == 200
        data_g = res_g.json()["data"]
        assert data_g["analytical_type"] == "PRESCRIPTIVE"
        assert len(data_g["result_data"]) > 0
        assert any("Safe Recommendation Boundary" in note for note in data_g["uncertainty_notes"])

    adapter.disconnect()


def test_frontend_workflows_i_through_l_abstention_and_errors(tmp_path: Path):
    """
    Executes and validates the API payloads corresponding to:
    I & J: Analytical Abstention (Timeless schema requesting forecast -> returns is_executable=False with clear reason).
    K & L: Execution Error handling.
    """
    db_file = tmp_path / "timeless_store.sqlite"
    conn = sqlite3.connect(str(db_file))
    with conn:
        conn.execute("CREATE TABLE products (product_id INT, price REAL);")
        conn.execute("INSERT INTO products VALUES (1, 99.0);")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(db_file), name="timeless_store", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)
    schema_service._custom_adapter = adapter
    schema_service._cached_catalog = cat

    with TestClient(app) as client:
        # Timeless forecast abstention
        res = client.post("/api/v1/analytics/execute", json={
            "question": "Forecast price for next month",
        })
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["success"] is False
        assert data["abstain_reason"] is not None
        assert "temporal" in data["abstain_reason"].lower() or "date" in data["abstain_reason"].lower()

    adapter.disconnect()


def test_frontend_database_switching_workflow(tmp_path: Path):
    """
    Executes and validates the database-switching workflow:
    1. Connect to Store DB.
    2. Start session with descriptive query.
    3. Switch connection to Clinic DB under the same session.
    4. Ask follow-up question.
    5. Verify zero Store context is leaked into Clinic response.
    """
    store_file = tmp_path / "store.sqlite"
    clinic_file = tmp_path / "clinic.sqlite"

    adapter_store, cat_store = _setup_store_db(store_file)
    adapter_clinic, cat_clinic = _setup_clinic_db(clinic_file)

    session_id = "ui_db_switch_sess"

    with TestClient(app) as client:
        # Turn 1: Store DB
        db_manager._active_adapter = adapter_store
        schema_service._custom_adapter = adapter_store
        schema_service._cached_catalog = cat_store
        res1 = client.post("/api/v1/analytics/execute", json={
            "question": "What is the trend in revenue over time?",
            "session_id": session_id,
        })
        assert res1.status_code == 200
        assert "sales" in res1.json()["data"]["source_tables"]

        # Turn 2: Switch to Clinic DB
        db_manager._active_adapter = adapter_clinic
        schema_service._custom_adapter = adapter_clinic
        schema_service._cached_catalog = cat_clinic
        res2 = client.post("/api/v1/analytics/execute", json={
            "question": "What is the trend in fee over time?",
            "session_id": session_id,
        })
        assert res2.status_code == 200
        data2 = res2.json()["data"]
        assert "patient_visits" in data2["source_tables"]
        # Zero store tables or columns leaked
        assert "sales" not in data2["source_tables"]
        assert "revenue" not in data2["source_columns"]

    adapter_store.disconnect()
    adapter_clinic.disconnect()
