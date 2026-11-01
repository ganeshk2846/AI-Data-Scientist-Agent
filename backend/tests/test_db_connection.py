"""
Tests for read-only database connectivity, immutability, and queries.
"""

import sqlite3
import pytest
from backend.app.db.connection import (
    get_readonly_connection,
    verify_database_immutability,
    check_database_readiness,
)


def test_verify_database_immutability():
    # Must succeed and return True because write probe is blocked
    is_immutable = verify_database_immutability()
    assert is_immutable is True


def test_readonly_select_query():
    with get_readonly_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM orders;")
        count = cursor.fetchone()[0]
        assert count == 17924


def test_readonly_write_blocked():
    with get_readonly_connection() as conn:
        cursor = conn.cursor()
        with pytest.raises(sqlite3.OperationalError) as exc_info:
            cursor.execute("INSERT INTO brands (brand_id, brand_name) VALUES (9999, 'Test');")
        assert "readonly" in str(exc_info.value).lower() or "attempt to write a readonly database" in str(exc_info.value).lower()


def test_check_database_readiness():
    status = check_database_readiness()
    assert status.connected is True
    assert status.read_only_verified is True
    assert status.table_count == 30
    assert status.total_rows == 334503
    assert status.size_bytes > 40_000_000
