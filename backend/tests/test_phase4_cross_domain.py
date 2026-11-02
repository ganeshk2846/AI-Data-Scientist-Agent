"""
backend/tests/test_phase4_cross_domain.py
Cross-Domain Validation Suite for Phase 4.
Proves that the exact same generic analytical engine operates across 4 distinct domains:
1. E-commerce (Orders & Revenue)
2. Healthcare (Patients & Treatment Costs)
3. University Library (Books & Checkout Loans)
4. Manufacturing (Machines & Downtime Optimization)
"""

from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


# =====================================================================
# Synthetic Domain Database Creators
# =====================================================================

def _setup_ecommerce(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE orders (order_id INT, customer_id INT, order_date TEXT, total_amount REAL);")
        for i in range(1, 25):
            conn.execute(f"INSERT INTO orders VALUES ({i}, 10, '2026-01-{i:02d}', {100.0 + i * 5});")
    conn.close()


def _setup_healthcare(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE hospital_treatments (treatment_id INT, department TEXT, treatment_date TEXT, cost REAL);")
        # Period 1 vs Period 2 for Cardiology vs Oncology
        conn.execute("INSERT INTO hospital_treatments VALUES (1, 'Cardiology', '2026-01-01', 500.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (2, 'Oncology', '2026-01-01', 800.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (3, 'Cardiology', '2026-02-01', 1200.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (4, 'Oncology', '2026-02-01', 850.0);")
    conn.close()


def _setup_library(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE book_loans (loan_id INT, book_category TEXT, loan_date TEXT, loan_count INT);")
        for i in range(1, 25):
            conn.execute(f"INSERT INTO book_loans VALUES ({i}, 'Computer Science', '2026-01-{i:02d}', {20 + i});")
    conn.close()


def _setup_manufacturing(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE machine_workorders (order_id INT, machine_name TEXT, order_date TEXT, downtime_hours REAL, maintenance_cost REAL);")
        conn.execute("INSERT INTO machine_workorders VALUES (1, 'CNC Lathe', '2026-01-01', 12.0, 450.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (2, 'Milling Center', '2026-01-01', 8.0, 300.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (3, 'Drill Press', '2026-01-01', 4.0, 150.0);")
    conn.close()


# =====================================================================
# Cross-Domain Tests
# =====================================================================

def test_domain_1_ecommerce_descriptive_and_predictive(tmp_path: Path):
    """Domain 1 (E-commerce): Verifies descriptive trend and forecasting workflows."""
    db_file = tmp_path / "ecom.sqlite"
    _setup_ecommerce(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="ecom_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # 1. Descriptive trend
    res_desc = analytical_orchestrator.analyze(
        question="What is the daily trend in total_amount over time?",
        catalog=cat,
    )
    assert res_desc.success is True
    assert res_desc.analytical_type == IntentCategory.DESCRIPTIVE
    assert len(res_desc.result_data) > 0
    assert "overall_growth_pct" in res_desc.computed_metrics

    # 2. Predictive forecast
    res_pred = analytical_orchestrator.analyze(
        question="Forecast total_amount for the next 7 days",
        catalog=cat,
    )
    assert res_pred.success is True
    assert res_pred.analytical_type == IntentCategory.PREDICTIVE
    assert len(res_pred.result_data) == 7
    assert "smape_pct" in res_pred.computed_metrics

    adapter.disconnect()


def test_domain_2_healthcare_diagnostic_driver_analysis(tmp_path: Path):
    """Domain 2 (Healthcare): Verifies diagnostic variance decomposition across departments."""
    db_file = tmp_path / "health.sqlite"
    _setup_healthcare(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="health_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # Diagnostic question
    res_diag = analytical_orchestrator.analyze(
        question="Why did cost increase across department between periods?",
        catalog=cat,
    )
    assert res_diag.success is True
    assert res_diag.analytical_type == IntentCategory.DIAGNOSTIC
    # Primary driver should be Cardiology (+700 vs Oncology +50)
    assert res_diag.computed_metrics.get("primary_driver") == "Cardiology"

    adapter.disconnect()


def test_domain_3_library_descriptive_and_forecasting(tmp_path: Path):
    """Domain 3 (University Library): Verifies loan volume forecasting without any e-commerce assumptions."""
    db_file = tmp_path / "lib.sqlite"
    _setup_library(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="lib_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    res_lib = analytical_orchestrator.analyze(
        question="Forecast loan_count for the next 7 days",
        catalog=cat,
    )
    assert res_lib.success is True
    assert res_lib.analytical_type == IntentCategory.PREDICTIVE
    assert res_lib.model_information.get("selected_model") is not None

    adapter.disconnect()


def test_domain_4_manufacturing_prescriptive_optimization(tmp_path: Path):
    """Domain 4 (Manufacturing): Verifies budget allocation and scenario simulation."""
    db_file = tmp_path / "mfg.sqlite"
    _setup_manufacturing(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="mfg_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # Prescriptive optimization
    res_opt = analytical_orchestrator.analyze(
        question="How should we allocate our $30k maintenance budget across machines?",
        catalog=cat,
    )
    assert res_opt.success is True
    assert res_opt.analytical_type == IntentCategory.PRESCRIPTIVE
    assert len(res_opt.recommended_next_steps) > 0
    assert any("Safe Recommendation Boundary" in u for u in res_opt.uncertainty_notes)

    adapter.disconnect()
