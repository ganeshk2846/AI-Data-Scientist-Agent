"""
backend/tests/test_phase4_analytical_planner.py
Unit tests for Phase 4 Analytical Planning Engine.
"""

from pathlib import Path
import sqlite3
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, IntentCategory
from backend.app.analysis.planner import analytical_planner
from backend.app.db.adapters import SQLiteAdapter
from backend.app.schema.service import SchemaService


def _create_sample_db(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE hospital_admissions (
                admission_id INTEGER PRIMARY KEY,
                patient_id INTEGER NOT NULL,
                admission_date TEXT NOT NULL,
                treatment_cost REAL NOT NULL,
                discharge_date TEXT
            );
        """)
        conn.execute("INSERT INTO hospital_admissions VALUES (1, 101, '2026-01-01', 1500.0, '2026-01-05');")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(path), name="test_hosp", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    return adapter, cat


def test_planner_creates_grounded_plan(tmp_path: Path):
    """Verifies planner identifies relevant table, time dimension, and target variable."""
    db_file = tmp_path / "hosp.sqlite"
    adapter, cat = _create_sample_db(db_file)

    plan = analytical_planner.create_plan(
        question="What is the monthly trend in treatment costs?",
        catalog=cat,
    )

    assert plan.intent == IntentCategory.DESCRIPTIVE
    assert "hospital_admissions" in plan.relevant_tables
    assert plan.time_dimension is not None
    assert "admission_date" in plan.time_dimension
    assert plan.target_variable is not None
    assert "treatment_cost" in plan.target_variable
    assert plan.is_executable is True
    assert plan.abstain_reason is None

    adapter.disconnect()


def test_planner_predictive_abstains_without_time_dimension(tmp_path: Path):
    """Verifies predictive planning abstains if target table lacks a date/time column."""
    db_file = tmp_path / "timeless.sqlite"
    conn = sqlite3.connect(str(db_file))
    with conn:
        conn.execute("CREATE TABLE products (product_id INTEGER, price REAL);")
        conn.execute("INSERT INTO products VALUES (1, 50.0);")
    conn.close()

    adapter = SQLiteAdapter(file_path=str(db_file), name="timeless_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    plan = analytical_planner.create_plan(
        question="Forecast product price for next month",
        catalog=cat,
    )

    assert plan.intent == IntentCategory.PREDICTIVE
    assert plan.is_executable is False
    assert "temporal/date column" in plan.abstain_reason

    adapter.disconnect()

