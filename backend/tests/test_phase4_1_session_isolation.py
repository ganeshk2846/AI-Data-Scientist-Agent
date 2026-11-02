"""
backend/tests/test_phase4_1_session_isolation.py
Unit and integration tests for Database-Aware Conversational Session Isolation.
Verifies that conversational context is strictly partitioned by (session_id, database_fingerprint)
and zero context leakage occurs when switching databases.
"""

from pathlib import Path
import sqlite3
from typing import Any, Tuple
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


def _setup_ecom_db(path: Path) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE orders (order_id INT, customer_id INT, order_date TEXT, total_amount REAL);")
        for i in range(1, 20):
            conn.execute(f"INSERT INTO orders VALUES ({i}, 10, '2026-01-{i:02d}', {100.0 + i * 5});")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="ecom_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    return adapter, cat


def _setup_health_db(path: Path) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE hospital_treatments (treatment_id INT, department TEXT, treatment_date TEXT, cost REAL);")
        for i in range(1, 20):
            conn.execute(f"INSERT INTO hospital_treatments VALUES ({i}, 'Cardiology', '2026-01-{i:02d}', {500.0 + i * 20});")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="health_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    return adapter, cat


def _setup_library_db(path: Path) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute("CREATE TABLE book_loans (loan_id INT, book_category TEXT, loan_date TEXT, loan_count INT);")
        for i in range(1, 20):
            conn.execute(f"INSERT INTO book_loans VALUES ({i}, 'Computer Science', '2026-01-{i:02d}', {20 + i});")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name="library_db", read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    return adapter, cat


def test_same_session_same_database_preserves_context(tmp_path: Path):
    """Verifies that follow-up queries within the same database successfully inherit context."""
    db_file = tmp_path / "ecom.sqlite"
    adapter, cat = _setup_ecom_db(db_file)
    db_manager._active_adapter = adapter

    session_id = "session_same_db_101"

    # Turn 1: Descriptive query establishes 'orders' and 'total_amount'
    r1 = analytical_orchestrator.analyze(
        question="What is the daily trend in total_amount over time?",
        session_id=session_id,
        catalog=cat,
    )
    assert r1.success is True
    assert "orders" in r1.source_tables

    # Turn 2: Follow-up query inherits 'orders' without explicit table mention
    r2 = analytical_orchestrator.analyze(
        question="Why did total_amount decrease between periods?",
        session_id=session_id,
        catalog=cat,
    )
    assert r2.success is True
    assert "orders" in r2.source_tables

    adapter.disconnect()
    analytical_orchestrator.clear_session(session_id)


def test_same_session_database_switch_prevents_context_leakage(tmp_path: Path):
    """
    Critical Isolation Test:
    1. Turn 1 on E-commerce sets context to 'orders' and 'total_amount'.
    2. User switches to Healthcare database within SAME session.
    3. Turn 2 must NOT inherit 'orders' or 'total_amount' from E-commerce.
    """
    ecom_file = tmp_path / "ecom.sqlite"
    health_file = tmp_path / "health.sqlite"

    adapter_ecom, cat_ecom = _setup_ecom_db(ecom_file)
    adapter_health, cat_health = _setup_health_db(health_file)

    session_id = "session_switch_202"

    # Turn 1: On E-commerce database
    db_manager._active_adapter = adapter_ecom
    r1 = analytical_orchestrator.analyze(
        question="What is the trend in total_amount?",
        session_id=session_id,
        catalog=cat_ecom,
    )
    assert r1.success is True
    assert "orders" in r1.source_tables

    # Turn 2: Switch active database to Healthcare under the SAME session
    db_manager._active_adapter = adapter_health
    r2 = analytical_orchestrator.analyze(
        question="What is the monthly trend in cost over time?",
        session_id=session_id,
        catalog=cat_health,
    )
    assert r2.success is True
    # Must be grounded strictly in healthcare, zero e-commerce leakage
    assert "hospital_treatments" in r2.source_tables
    assert "orders" not in r2.source_tables
    assert "total_amount" not in r2.source_columns

    adapter_ecom.disconnect()
    adapter_health.disconnect()
    analytical_orchestrator.clear_session(session_id)


def test_healthcare_to_library_no_context_leakage(tmp_path: Path):
    """Verifies sequential switching from Healthcare to Library prevents cross-domain contamination."""
    health_file = tmp_path / "health.sqlite"
    lib_file = tmp_path / "lib.sqlite"

    adapter_health, cat_health = _setup_health_db(health_file)
    adapter_lib, cat_lib = _setup_library_db(lib_file)

    session_id = "session_switch_303"

    # Healthcare turn
    db_manager._active_adapter = adapter_health
    r_h = analytical_orchestrator.analyze(
        question="What is the trend in cost over time?",
        session_id=session_id,
        catalog=cat_health,
    )
    assert r_h.success is True
    assert "hospital_treatments" in r_h.source_tables

    # Switch to Library
    db_manager._active_adapter = adapter_lib
    r_l = analytical_orchestrator.analyze(
        question="Forecast loan_count for the next 7 days",
        session_id=session_id,
        catalog=cat_lib,
    )
    assert r_l.success is True
    assert "book_loans" in r_l.source_tables
    assert "hospital_treatments" not in r_l.source_tables
    assert "department" not in r_l.source_columns

    adapter_health.disconnect()
    adapter_lib.disconnect()
    analytical_orchestrator.clear_session(session_id)


def test_two_distinct_sessions_are_isolated(tmp_path: Path):
    """Verifies that separate sessions accessing the same database remain isolated."""
    db_file = tmp_path / "ecom.sqlite"
    adapter, cat = _setup_ecom_db(db_file)
    db_manager._active_adapter = adapter

    s1 = "user_session_A"
    s2 = "user_session_B"

    r1 = analytical_orchestrator.analyze(
        question="What is the daily trend in total_amount over time?",
        session_id=s1,
        catalog=cat,
    )
    assert r1.success is True

    # Session 2 asks an independent question
    r2 = analytical_orchestrator.analyze(
        question="What are the summary statistics for total_amount?",
        session_id=s2,
        catalog=cat,
    )
    assert r2.success is True

    # Both sessions have distinct isolated cached states
    fp = cat.source_fingerprint
    assert (s1, fp) in analytical_orchestrator._session_cache
    assert (s2, fp) in analytical_orchestrator._session_cache

    adapter.disconnect()
    analytical_orchestrator.clear_session(s1)
    analytical_orchestrator.clear_session(s2)
