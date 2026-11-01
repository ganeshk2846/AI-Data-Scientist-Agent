"""
Strictly read-only database connection manager for ecommerce.sqlite.
Enforces URI mode=ro, validates immutability, and provides connection context managers.
"""

from contextlib import contextmanager
import os
from pathlib import Path
import sqlite3
from typing import Generator, Optional
from backend.app.core.config import settings
from backend.app.core.errors import DatabaseError, DatabaseReadOnlyViolationError
from backend.app.core.logging import logger
from backend.app.core.models import DatabaseReadiness


def get_readonly_uri(db_path: Path) -> str:
    """Builds a strict SQLite read-only URI."""
    clean_path = db_path.resolve().as_posix()
    return f"file:{clean_path}?mode=ro"


@contextmanager
def get_readonly_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager that yields an active read-only connection to ecommerce.sqlite.
    Ensures connection is closed cleanly and rows are accessible as dict-like objects.
    """
    db_path = settings.resolved_ecommerce_db_path
    if not db_path.exists():
        raise DatabaseError(
            message=f"Database file not found at expected path: {db_path}",
            details={"path": str(db_path)},
        )

    uri = get_readonly_uri(db_path)
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True, timeout=settings.SQL_QUERY_TIMEOUT_SECONDS)
        conn.row_factory = sqlite3.Row
        yield conn
    except sqlite3.OperationalError as e:
        logger.error(f"Database operational error: {e}")
        raise DatabaseError(message=f"Database connection error: {str(e)}", details={"uri": uri})
    finally:
        if conn:
            conn.close()


def verify_database_immutability() -> bool:
    """
    Probes the database to verify write attempts are blocked by SQLite.
    Returns True if write was blocked with OperationalError.
    Raises DatabaseReadOnlyViolationError if write succeeded.
    """
    db_path = settings.resolved_ecommerce_db_path
    if not db_path.exists():
        raise DatabaseError(f"Database file not found at: {db_path}")

    uri = get_readonly_uri(db_path)
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        cursor = conn.cursor()
        cursor.execute("CREATE TABLE IF NOT EXISTS __probe_violation__ (id INT);")
        conn.commit()
        # If execution reached here, write was allowed -> Violation!
        raise DatabaseReadOnlyViolationError("Database is writable! Strict read-only mode required.")
    except sqlite3.OperationalError as e:
        # Expected behavior: "attempt to write a readonly database"
        if "readonly" in str(e).lower() or "attempt to write a readonly database" in str(e).lower():
            return True
        logger.warning(f"Unexpected operational error during write probe: {e}")
        return True
    finally:
        if conn:
            conn.close()


def check_database_readiness() -> DatabaseReadiness:
    """
    Inspects database state, connectivity, table count, and row count.
    """
    db_path = settings.resolved_ecommerce_db_path
    if not db_path.exists():
        return DatabaseReadiness(
            connected=False,
            read_only_verified=False,
            path=str(db_path),
            error="Database file does not exist on disk",
        )

    try:
        read_only_ok = verify_database_immutability()
        with get_readonly_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tbl_count = cur.fetchone()[0]

            # Quick row count across all tables
            cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = [r[0] for r in cur.fetchall()]
            total_rows = 0
            for t in tables:
                cur.execute(f'SELECT COUNT(*) FROM "{t}";')
                total_rows += cur.fetchone()[0]

            file_size = os.path.getsize(db_path)

            return DatabaseReadiness(
                connected=True,
                read_only_verified=read_only_ok,
                path=str(db_path),
                size_bytes=file_size,
                table_count=tbl_count,
                total_rows=total_rows,
            )
    except Exception as e:
        logger.error(f"Failed database readiness check: {e}")
        return DatabaseReadiness(
            connected=False,
            read_only_verified=False,
            path=str(db_path),
            error=str(e),
        )
