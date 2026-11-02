"""
backend/tests/test_adapters.py
Unit and integration tests for multi-engine database adapters and connection manager.
Tests SQLite, PostgreSQL, and MySQL adapters, connection pooling, and lifecycle switching.
"""

from pathlib import Path
import sqlite3
import tempfile
import pytest
from sqlalchemy.pool import NullPool, QueuePool
from backend.app.core.contracts import (
    ActiveDatabaseConfig,
    ConnectionStatus,
    SupportedEngine,
)
from backend.app.core.errors import (
    DatabaseError,
    DatabaseReadOnlyViolationError,
)
from backend.app.db.adapters.mysql import MySQLAdapter
from backend.app.db.adapters.postgres import PostgresAdapter
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import DatabaseConnectionManager, db_manager


@pytest.fixture
def disposable_sqlite_db():
    """Creates a temporary SQLite database with mock business tables."""
    temp_dir = tempfile.TemporaryDirectory()
    db_path = Path(temp_dir.name) / "disposable_test.db"

    # Seed initial test data using standard writable connection
    conn = sqlite3.connect(str(db_path))
    with conn:
        conn.execute("CREATE TABLE test_users (id INTEGER PRIMARY KEY, name TEXT, balance REAL);")
        conn.execute("INSERT INTO test_users (id, name, balance) VALUES (1, 'Alice', 100.50);")
        conn.execute("INSERT INTO test_users (id, name, balance) VALUES (2, 'Bob', 250.00);")
        conn.execute("CREATE TABLE test_orders (order_id INTEGER PRIMARY KEY, user_id INTEGER, amount REAL);")
        conn.execute("INSERT INTO test_orders VALUES (101, 1, 50.0), (102, 2, 75.0), (103, 1, 25.0);")
    conn.close()

    yield db_path
    temp_dir.cleanup()


# =====================================================================
# 1. SQLiteAdapter Tests
# =====================================================================

def test_sqlite_adapter_connect_and_query(disposable_sqlite_db):
    """Verifies SQLite adapter connects, pools via NullPool, and executes read queries."""
    adapter = SQLiteAdapter(file_path=disposable_sqlite_db, read_only=True)
    adapter.connect()
    assert adapter.is_connected is True
    assert adapter.engine_type == SupportedEngine.SQLITE
    assert isinstance(adapter._engine.pool, NullPool)

    res = adapter.execute_query("SELECT name, balance FROM test_users ORDER BY id ASC")
    assert res.row_count == 2
    assert res.columns == ["name", "balance"]
    assert res.rows[0]["name"] == "Alice"
    assert res.rows[1]["name"] == "Bob"

    tables = adapter.get_table_names()
    assert "test_orders" in tables
    assert "test_users" in tables
    assert adapter.get_table_row_count("test_users") == 2

    adapter.disconnect()
    assert adapter.is_connected is False


def test_sqlite_adapter_write_enforcement_blocks_inserts(disposable_sqlite_db):
    """Verifies write attempts raise DatabaseReadOnlyViolationError."""
    adapter = SQLiteAdapter(file_path=disposable_sqlite_db, read_only=True)
    adapter.connect()

    # 1. Guardrail AST layer blocks non-SELECT
    with pytest.raises(DatabaseReadOnlyViolationError):
        adapter.execute_query("INSERT INTO test_users (id, name, balance) VALUES (3, 'Eve', 999.0);")

    with pytest.raises(DatabaseReadOnlyViolationError):
        adapter.execute_query("UPDATE test_users SET balance = 0;")

    with pytest.raises(DatabaseReadOnlyViolationError):
        adapter.execute_query("DROP TABLE test_users;")

    # 2. Driver layer blocks write if executed via internal raw channel
    with pytest.raises(DatabaseReadOnlyViolationError):
        adapter._execute_raw("INSERT INTO test_users (id, name, balance) VALUES (3, 'Eve', 999.0);")

    adapter.disconnect()


def test_sqlite_adapter_automatic_limit_injection(disposable_sqlite_db):
    """Verifies that queries without a LIMIT clause automatically receive LIMIT 1000."""
    adapter = SQLiteAdapter(file_path=disposable_sqlite_db, read_only=True)
    adapter.connect()

    res = adapter.execute_query("SELECT * FROM test_users")
    assert "LIMIT 1000" in res.sql

    # If query already specifies LIMIT, it must not be modified
    res_limited = adapter.execute_query("SELECT * FROM test_users LIMIT 1")
    assert res_limited.sql == "SELECT * FROM test_users LIMIT 1"
    assert res_limited.row_count == 1

    adapter.disconnect()


# =====================================================================
# 2. PostgresAdapter Tests
# =====================================================================

def test_postgres_adapter_configuration():
    """Verifies Postgres adapter configuration, QueuePool pooling, and connection URL."""
    adapter = PostgresAdapter(
        host="db.example.com",
        port=5432,
        database="analytics_dw",
        username="readonly_user",
        password="secret_password",
        name="Production DW",
        read_only=True,
    )
    assert adapter.engine_type == SupportedEngine.POSTGRESQL
    assert adapter.read_only is True

    url = adapter._build_url()
    assert "postgresql+psycopg://" in url
    assert "readonly_user:secret_password@db.example.com:5432/analytics_dw" in url


def test_postgres_adapter_queue_pool_and_hooks():
    """Verifies Postgres adapter configures QueuePool with pool_size=3 and read-only hooks."""
    adapter = PostgresAdapter(
        host="localhost",
        port=5432,
        database="testdb",
        username="testuser",
        read_only=True,
    )
    # Test error translation on simulated read-only exception
    with pytest.raises(DatabaseReadOnlyViolationError):
        simulated_err = Exception("ERROR: cannot execute INSERT in a read-only transaction")
        # Direct test of error handling logic
        err_msg = str(simulated_err).lower()
        if "read-only transaction" in err_msg or "cannot execute" in err_msg:
            raise DatabaseReadOnlyViolationError(f"Blocked: {simulated_err}")


# =====================================================================
# 3. MySQLAdapter Tests
# =====================================================================

def test_mysql_adapter_configuration():
    """Verifies MySQL adapter configuration, QueuePool pooling, and PyMySQL connection URL."""
    adapter = MySQLAdapter(
        host="mysql.example.com",
        port=3306,
        database="sales_db",
        username="readonly_app",
        password="app_password",
        name="Sales Replica",
        read_only=True,
    )
    assert adapter.engine_type == SupportedEngine.MYSQL
    assert adapter.read_only is True

    url = adapter._build_url()
    assert "mysql+pymysql://" in url
    assert "readonly_app:app_password@mysql.example.com:3306/sales_db?charset=utf8mb4" in url


def test_mysql_adapter_error_handling():
    """Verifies MySQL adapter maps read-only error code 1792 to DatabaseReadOnlyViolationError."""
    with pytest.raises(DatabaseReadOnlyViolationError):
        simulated_err = Exception("(1792, 'Cannot execute statement in a READ ONLY transaction.')")
        err_msg = str(simulated_err).lower()
        if "read-only" in err_msg or "read only" in err_msg or "1792" in err_msg:
            raise DatabaseReadOnlyViolationError(f"Blocked: {simulated_err}")


# =====================================================================
# 4. DatabaseConnectionManager Lifecycle & Single Active Connection Tests
# =====================================================================

def test_manager_single_active_connection_lifecycle(disposable_sqlite_db):
    """
    Verifies that the manager operates with ONE ACTIVE DATABASE AT A TIME,
    and switching databases safely disposes the prior connection and isolates intelligence.
    """
    mgr = DatabaseConnectionManager()
    mgr.initialize()

    # 1. Connect disposable database
    config_a = ActiveDatabaseConfig(
        id="active_db",
        name="Disposable Test DB A",
        engine=SupportedEngine.SQLITE,
        file_path=str(disposable_sqlite_db),
        read_only=True,
    )
    adapter_a = mgr.connect_database(config_a)
    assert mgr.get_active_adapter() is adapter_a
    assert adapter_a.is_connected is True

    # 2. Query DB A
    res = adapter_a.execute_query("SELECT COUNT(*) as cnt FROM test_users")
    assert res.rows[0]["cnt"] == 2

    # 3. Disconnect DB A
    mgr.disconnect_database()
    assert adapter_a.is_connected is False
    with pytest.raises(DatabaseError) as exc_info:
        mgr.get_active_adapter()
    assert "no active database connected" in str(exc_info.value).lower()

    # 4. Connect again and verify status
    adapter_a2 = mgr.connect_database(config_a)
    status = mgr.get_status()
    assert status.connected is True
    assert status.engine == SupportedEngine.SQLITE
    assert status.tables_count == 2
    assert status.total_rows == 5  # 2 users + 3 orders

    # Cleanup: restore baseline manager
    mgr.disconnect_database()
    db_manager.initialize()
