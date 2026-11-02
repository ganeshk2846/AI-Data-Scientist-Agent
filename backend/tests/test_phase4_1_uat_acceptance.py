"""
backend/tests/test_phase4_1_uat_acceptance.py
Phase 4.1 Controlled User Acceptance Testing (UAT) Matrix.

Validates end-to-end analytical intelligence across 4 distinct domains:
1. E-Commerce (Orders, Revenue, Marketing Budget)
2. Healthcare (Treatments, Department Costs, Resource Allocation)
3. University Library (Book Categories, Loans, Circulation Demand)
4. Manufacturing (Machines, Downtime Hours, Maintenance Allocation)

Covers all 4 analytical capabilities (Descriptive, Diagnostic, Predictive, Prescriptive)
plus multi-intent composite sequences with structured claim validation and safe decision boundaries.
"""

from pathlib import Path
import sqlite3
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory, ClaimType
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


# =====================================================================
# Domain Synthetic Data Builders
# =====================================================================

def _create_ecommerce_db(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE orders (
                order_id INTEGER PRIMARY KEY,
                category TEXT,
                order_date TEXT,
                total_amount REAL
            );
        """)
        # 30 daily observations across 2 categories
        for i in range(1, 31):
            conn.execute(f"INSERT INTO orders VALUES ({i*2-1}, 'Electronics', '2026-01-{i:02d}', {120.0 + i * 3.5});")
            conn.execute(f"INSERT INTO orders VALUES ({i*2}, 'Apparel', '2026-01-{i:02d}', {80.0 + i * 1.5});")
    conn.close()


def _create_healthcare_db(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE hospital_treatments (
                treatment_id INTEGER PRIMARY KEY,
                department TEXT,
                treatment_date TEXT,
                cost REAL
            );
        """)
        # Period 1 vs Period 2 data for Cardiology and Oncology
        conn.execute("INSERT INTO hospital_treatments VALUES (1, 'Cardiology', '2026-01-01', 5000.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (2, 'Oncology', '2026-01-01', 8000.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (3, 'Cardiology', '2026-02-01', 14000.0);")
        conn.execute("INSERT INTO hospital_treatments VALUES (4, 'Oncology', '2026-02-01', 8500.0);")
    conn.close()


def _create_library_db(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE book_loans (
                loan_id INTEGER PRIMARY KEY,
                book_category TEXT,
                loan_date TEXT,
                loan_count INTEGER
            );
        """)
        for i in range(1, 28):
            conn.execute(f"INSERT INTO book_loans VALUES ({i}, 'Computer Science', '2026-01-{i:02d}', {30 + i * 2});")
            conn.execute(f"INSERT INTO book_loans VALUES ({i+100}, 'History', '2026-01-{i:02d}', {15 + (i % 5)});")
    conn.close()


def _create_manufacturing_db(path: Path):
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("""
            CREATE TABLE machine_workorders (
                order_id INTEGER PRIMARY KEY,
                machine_name TEXT,
                order_date TEXT,
                downtime_hours REAL,
                maintenance_cost REAL
            );
        """)
        conn.execute("INSERT INTO machine_workorders VALUES (1, 'CNC Lathe', '2026-01-01', 45.0, 12000.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (2, 'Milling Center', '2026-01-01', 12.0, 4500.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (3, 'Drill Press', '2026-01-01', 5.0, 1800.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (4, 'CNC Lathe', '2026-02-01', 60.0, 15000.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (5, 'Milling Center', '2026-02-01', 10.0, 4200.0);")
        conn.execute("INSERT INTO machine_workorders VALUES (6, 'Drill Press', '2026-02-01', 6.0, 1900.0);")
    conn.close()


# =====================================================================
# UAT Domain 1: E-COMMERCE
# =====================================================================

def test_uat_domain_1_ecommerce_acceptance(tmp_path: Path):
    """
    UAT-ECOM-01: E-commerce diagnostic, predictive, prescriptive & composite flows.
    """
    db_file = tmp_path / "uat_ecom.sqlite"
    _create_ecommerce_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="uat_ecom", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # 1. Descriptive trend
    res_desc = analytical_orchestrator.analyze("What is the daily trend in total_amount?", catalog=cat)
    assert res_desc.success is True
    assert res_desc.analytical_type == IntentCategory.DESCRIPTIVE
    assert len(res_desc.result_data) > 0
    assert "overall_growth_pct" in res_desc.computed_metrics

    # 2. Predictive forecast with recursive multi-step LightGBM or Naive/ARIMA
    res_pred = analytical_orchestrator.analyze("Forecast total_amount for the next 7 days", catalog=cat)
    assert res_pred.success is True
    assert res_pred.analytical_type == IntentCategory.PREDICTIVE
    assert len(res_pred.result_data) == 7
    # Non-negative volume metric intervals
    for pt in res_pred.result_data:
        assert pt["lower_bound"] >= 0.0
        assert pt["predicted_value"] >= pt["lower_bound"]
        assert pt["upper_bound"] >= pt["predicted_value"]

    # 3. Prescriptive optimization (concave diminishing returns)
    res_opt = analytical_orchestrator.analyze(
        "How should we allocate our $25000 marketing budget across category?",
        catalog=cat,
    )
    assert res_opt.success is True
    assert res_opt.analytical_type == IntentCategory.PRESCRIPTIVE
    assert res_opt.computed_metrics.get("is_optimal") is True
    assert res_opt.computed_metrics.get("constraint_residual") < 1e-4

    # 4. Multi-intent composite workflow: "What caused the revenue decrease last quarter and how can we improve it?"
    res_comp = analytical_orchestrator.analyze(
        "What caused the revenue decrease across category and how can we optimize our $25000 budget?",
        catalog=cat,
    )
    assert res_comp.success is True
    assert "composite_intents" in res_comp.model_information
    assert len(res_comp.model_information["composite_intents"]) == 2

    # Structured claim faithfulness
    assert res_comp.faithfulness_report is not None
    assert len(res_comp.faithfulness_report.structured_claims) > 0

    adapter.disconnect()


# =====================================================================
# UAT Domain 2: HEALTHCARE
# =====================================================================

def test_uat_domain_2_healthcare_acceptance(tmp_path: Path):
    """
    UAT-HLTH-01: Healthcare cost drivers, multi-intent diagnosis & resource allocation.
    """
    db_file = tmp_path / "uat_health.sqlite"
    _create_healthcare_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="uat_health", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # 1. Diagnostic driver detection
    res_diag = analytical_orchestrator.analyze(
        "Which treatment categories are associated with increasing costs across department?",
        catalog=cat,
    )
    assert res_diag.success is True
    assert res_diag.analytical_type == IntentCategory.DIAGNOSTIC
    assert res_diag.computed_metrics.get("primary_driver") == "Cardiology"

    # Structured claim verification: driver contribution claim
    assert res_diag.faithfulness_report is not None
    claims = res_diag.faithfulness_report.structured_claims
    driver_claims = [c for c in claims if c.claim_type == ClaimType.DRIVER_CONTRIBUTION]
    assert len(driver_claims) > 0
    assert driver_claims[0].verified is True

    # 2. Prescriptive optimization across hospital departments
    res_opt = analytical_orchestrator.analyze(
        "How should we allocate our $50000 healthcare budget across department?",
        catalog=cat,
    )
    assert res_opt.success is True
    assert res_opt.analytical_type == IntentCategory.PRESCRIPTIVE
    assert res_opt.computed_metrics.get("is_optimal") is True

    # 3. Composite diagnostic -> prescriptive workflow
    res_comp = analytical_orchestrator.analyze(
        "Which treatment categories are associated with increasing costs across department, and what resource allocation options should be evaluated for 50000 budget?",
        catalog=cat,
    )
    assert res_comp.success is True
    assert "composite_intents" in res_comp.model_information

    adapter.disconnect()


# =====================================================================
# UAT Domain 3: UNIVERSITY LIBRARY
# =====================================================================

def test_uat_domain_3_library_acceptance(tmp_path: Path):
    """
    UAT-LIBR-01: University library loan volume trends, predictive demand & composites.
    """
    db_file = tmp_path / "uat_lib.sqlite"
    _create_library_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="uat_lib", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # 1. Descriptive trend
    res_desc = analytical_orchestrator.analyze(
        "What is the daily trend in loan_count over time?",
        catalog=cat,
    )
    assert res_desc.success is True
    assert res_desc.analytical_type == IntentCategory.DESCRIPTIVE

    # 2. Predictive demand forecasting
    res_pred = analytical_orchestrator.analyze(
        "What borrowing demand should we prepare for in the next 7 days for loan_count?",
        catalog=cat,
    )
    assert res_pred.success is True
    assert res_pred.analytical_type == IntentCategory.PREDICTIVE
    assert len(res_pred.result_data) == 7
    # Zero e-commerce leakage
    for u in res_pred.uncertainty_notes:
        assert "e-commerce" not in u.lower()
        assert "revenue" not in u.lower()

    # 3. Composite descriptive -> predictive workflow
    res_comp = analytical_orchestrator.analyze(
        "What is the daily trend in loan_count over time, and what is the forecast for next 7 days?",
        catalog=cat,
    )
    assert res_comp.success is True
    assert "composite_intents" in res_comp.model_information

    adapter.disconnect()


# =====================================================================
# UAT Domain 4: MANUFACTURING
# =====================================================================

def test_uat_domain_4_manufacturing_acceptance(tmp_path: Path):
    """
    UAT-MFG-01: Manufacturing downtime drivers, predictive trends & budget optimization.
    """
    db_file = tmp_path / "uat_mfg.sqlite"
    _create_manufacturing_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="uat_mfg", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # 1. Diagnostic downtime driver identification
    res_diag = analytical_orchestrator.analyze(
        "Which machines contribute most to downtime_hours across machine_name?",
        catalog=cat,
    )
    assert res_diag.success is True
    assert res_diag.analytical_type == IntentCategory.DIAGNOSTIC
    assert res_diag.computed_metrics.get("primary_driver") == "CNC Lathe"

    # 2. Prescriptive optimization with safe boundary enforcement
    res_opt = analytical_orchestrator.analyze(
        "How should the maintenance budget of $20000 be allocated across machine_name?",
        catalog=cat,
    )
    assert res_opt.success is True
    assert res_opt.analytical_type == IntentCategory.PRESCRIPTIVE
    assert res_opt.computed_metrics.get("is_optimal") is True
    assert any("Safe Recommendation Boundary" in u for u in res_opt.uncertainty_notes)
    # Check that allocations respect total budget within tolerance
    allocations = res_opt.computed_metrics.get("optimal_allocations", {})
    assert len(allocations) > 0
    total_alloc = sum(allocations.values())
    assert abs(total_alloc - 20000.0) <= 0.05

    # 3. Composite diagnostic -> prescriptive workflow
    res_comp = analytical_orchestrator.analyze(
        "Which machines contribute most to downtime_hours across machine_name, and how should the maintenance budget of $20000 be allocated across machine_name?",
        catalog=cat,
    )
    assert res_comp.success is True
    assert "composite_intents" in res_comp.model_information

    adapter.disconnect()

