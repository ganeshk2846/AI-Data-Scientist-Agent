"""
backend/tests/test_phase4_1_cache_isolation.py
Unit tests for Database-Aware Session and Result Caching.
Verifies:
1. Cache entries incorporate database fingerprint.
2. Incompatible databases never share cached analytical results.
3. Database cache invalidation cleanly removes cached artifacts.
"""

from pathlib import Path
import sqlite3
from typing import Any, Tuple
import pytest

from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


def _create_db(path: Path, tbl_name: str, col_name: str) -> Tuple[SQLiteAdapter, Any]:
    conn = sqlite3.connect(str(path))
    with conn:
        conn.execute(f"CREATE TABLE {tbl_name} (id INT, date_col TEXT, {col_name} REAL);")
        for i in range(1, 15):
            conn.execute(f"INSERT INTO {tbl_name} VALUES ({i}, '2026-01-{i:02d}', {50.0 + i*5});")
    conn.close()
    adapter = SQLiteAdapter(file_path=str(path), name=path.stem, read_only=True)
    adapter.connect()
    svc = SchemaService(db_path=str(path))
    cat = svc.profile_database(force_refresh=True)
    return adapter, cat


def test_cache_keys_incorporate_database_fingerprint(tmp_path: Path):
    """Verifies that session and result caches partition data by database fingerprint."""
    db1_path = tmp_path / "db1.sqlite"
    db2_path = tmp_path / "db2.sqlite"

    adapter1, cat1 = _create_db(db1_path, "sales", "amount")
    adapter2, cat2 = _create_db(db2_path, "expenses", "cost")

    session_id = "test_cache_sess_1"

    # Run on DB1
    db_manager._active_adapter = adapter1
    r1 = analytical_orchestrator.analyze(
        question="What is the trend in amount over time?",
        session_id=session_id,
        catalog=cat1,
    )
    assert r1.success is True

    fp1 = cat1.source_fingerprint
    fp2 = cat2.source_fingerprint
    assert fp1 != fp2

    # Verify session cache is keyed by (session_id, fp1)
    assert (session_id, fp1) in analytical_orchestrator._session_cache
    assert (session_id, fp2) not in analytical_orchestrator._session_cache

    # Run on DB2
    db_manager._active_adapter = adapter2
    r2 = analytical_orchestrator.analyze(
        question="What is the trend in cost over time?",
        session_id=session_id,
        catalog=cat2,
    )
    assert r2.success is True

    # Switching database must have cleared the old (session_id, fp1) context
    assert (session_id, fp1) not in analytical_orchestrator._session_cache
    assert (session_id, fp2) in analytical_orchestrator._session_cache

    adapter1.disconnect()
    adapter2.disconnect()
    analytical_orchestrator.clear_session(session_id)


def test_database_cache_clearing(tmp_path: Path):
    """Verifies clear_database_cache removes all entries for a specific fingerprint."""
    db_path = tmp_path / "target_db.sqlite"
    adapter, cat = _create_db(db_path, "items", "val")
    db_manager._active_adapter = adapter

    sess = "clear_target_sess"
    r = analytical_orchestrator.analyze(
        question="What is the trend in val over time?",
        session_id=sess,
        catalog=cat,
    )
    assert r.success is True

    fp = cat.source_fingerprint
    assert (sess, fp) in analytical_orchestrator._session_cache

    # Clear database cache
    analytical_orchestrator.clear_database_cache(fp)
    assert (sess, fp) not in analytical_orchestrator._session_cache

    adapter.disconnect()
    analytical_orchestrator.clear_session(sess)

