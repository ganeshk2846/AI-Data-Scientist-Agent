"""
backend/tests/test_phase4_1_2_multitable_planner.py
Targeted test suite for DEF-02: Schema-Aware Multi-Table and Temporal Dimension Ranking.
Verifies that when predictive demand queries target dimension entities (e.g. books),
the planner discovers and ranks connected event/fact tables (e.g. loans) possessing temporal dimensions
via introspected foreign keys, without inventing ungrounded joins.
"""

from pathlib import Path
import sqlite3
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.data_extractor import analytical_data_extractor
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.analysis.planner import analytical_planner
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


def _setup_library_multitable_db(db_path: Path):
    """Sets up an isolated temporary multi-table library schema with explicit foreign keys."""
    conn = sqlite3.connect(str(db_path))
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE books (
            book_id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            author TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE loans (
            loan_id INTEGER PRIMARY KEY,
            book_id INTEGER NOT NULL,
            patron_id INTEGER NOT NULL,
            loan_date TEXT NOT NULL,
            return_date TEXT,
            loan_count INTEGER NOT NULL,
            FOREIGN KEY (book_id) REFERENCES books (book_id)
        )
    """)

    cur.execute("""
        CREATE TABLE departments (
            dept_id INTEGER PRIMARY KEY,
            dept_name TEXT NOT NULL,
            faculty_count INTEGER NOT NULL
        )
    """)

    # Seed records
    categories = ["Fiction", "Science", "History", "Engineering"]
    for i in range(1, 11):
        cat = categories[i % len(categories)]
        cur.execute(
            "INSERT INTO books (book_id, title, author, category, price) VALUES (?, ?, ?, ?, ?)",
            (i, f"Book Title {i}", f"Author {i}", cat, 25.0 + i * 2.5),
        )

    for i in range(1, 41):
        b_id = (i % 10) + 1
        day = f"2025-01-{(i % 28) + 1:02d}"
        cur.execute(
            "INSERT INTO loans (loan_id, book_id, patron_id, loan_date, return_date, loan_count) VALUES (?, ?, ?, ?, ?, ?)",
            (i, b_id, 100 + i, day, None, 1 + (i % 3)),
        )

    cur.execute("INSERT INTO departments (dept_id, dept_name, faculty_count) VALUES (1, 'Engineering', 25)")
    cur.execute("INSERT INTO departments (dept_id, dept_name, faculty_count) VALUES (2, 'Humanities', 18)")

    conn.commit()
    conn.close()


def test_library_loans_books_fk_resolution(tmp_path: Path):
    """Verifies that loans is discovered as the temporal event table when query targets book demand."""
    db_file = tmp_path / "lib_multi.sqlite"
    _setup_library_multitable_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="lib_test_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # Question targeting book borrowing demand
    q = "Which book categories are likely to experience the highest borrowing demand next semester?"
    plan = analytical_planner.create_plan(question=q, catalog=cat)

    assert plan.is_executable is True
    assert plan.intent == IntentCategory.PREDICTIVE
    # DEF-02: loans should be prioritized first as the event table with temporal column, books second
    assert "loans" in plan.relevant_tables
    assert "books" in plan.relevant_tables
    assert plan.relevant_tables[0] == "loans"
    assert plan.time_dimension == "loans.loan_date"

    # Synthesize extraction SQL
    sql = analytical_data_extractor._synthesize_extraction_sql(plan, cat)
    assert sql is not None
    assert "FROM loans JOIN books ON" in sql
    assert "loans.book_id = books.book_id" in sql
    assert "ORDER BY loans.loan_date ASC" in sql

    # Execute extraction
    success, df, queries, err = analytical_data_extractor.extract_data_for_plan(plan, cat)
    assert success is True
    assert df is not None
    assert not df.empty
    assert "loan_date" in df.columns or "loans.loan_date" in df.columns
    assert "category" in df.columns or "books.category" in df.columns

    adapter.disconnect()


def test_temporal_abstention_on_unconnected_dimension_table(tmp_path: Path):
    """Verifies safe abstention when query targets a dimension table with no date and no FK event table."""
    db_file = tmp_path / "lib_unconnected.sqlite"
    _setup_library_multitable_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="lib_unconn_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    # Departments has no date column and no FK connection to loans
    q = "Forecast demand for university departments for next month"
    plan = analytical_planner.create_plan(question=q, catalog=cat)

    # Must safely abstain without fabricating temporal columns
    assert plan.is_executable is False
    assert plan.time_dimension is None
    assert "temporal/date column" in (plan.abstain_reason or "")

    adapter.disconnect()


def test_full_multitable_forecasting_pipeline(tmp_path: Path):
    """Verifies end-to-end multi-table predictive execution through AnalyticalOrchestrator."""
    db_file = tmp_path / "lib_e2e.sqlite"
    _setup_library_multitable_db(db_file)

    adapter = SQLiteAdapter(file_path=str(db_file), name="lib_e2e_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter
    svc = SchemaService(db_path=str(db_file))
    cat = svc.profile_database(force_refresh=True)

    q = "Forecast borrowing demand for book categories over the next 7 days"
    res = analytical_orchestrator.analyze(question=q, catalog=cat)

    assert res.success is True
    assert res.analytical_type == IntentCategory.PREDICTIVE
    assert len(res.result_data) > 0
    assert "selected_model" in res.model_information
    assert any("forecast" in f.lower() or "projected" in f.lower() for f in res.findings)

    adapter.disconnect()

