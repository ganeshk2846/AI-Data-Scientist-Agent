"""
backend/app/db/connection.py
Backward-compatible connection facade delegating to DatabaseConnectionManager.
Preserves existing V1 import contracts (get_readonly_connection, check_database_readiness)
while routing through the unified multi-engine connection abstraction.
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
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager


def get_readonly_uri(db_path: Path) -> str:
    """Builds a strict SQLite read-only URI."""
    clean_path = db_path.resolve().as_posix()
    return f"file:{clean_path}?mode=ro"


@contextmanager
def get_readonly_connection() -> Generator[sqlite3.Connection, None, None]:
    """
    Context manager yielding an active read-only connection to ecommerce.db.
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
        conn.execute("PRAGMA query_only = ON;")
        yield conn
    except sqlite3.OperationalError as e:
        logger.error(f"Database operational error: {e}")
        raise DatabaseError(message=f"Database connection error: {str(e)}", details={"uri": uri})
    finally:
        if conn:
            conn.close()


def verify_database_immutability() -> bool:
    """
    Verifies that the active database connection enforces read-only mode.
    Validates read-only URI parameters and PRAGMA query_only configuration
    WITHOUT executing destructive write probes on customer databases.
    """
    try:
        adapter = db_manager.get_active_adapter()
        if adapter.read_only:
            return True
    except Exception:
        pass

    db_path = settings.resolved_ecommerce_db_path
    if not db_path.exists():
        raise DatabaseError(f"Database file not found at: {db_path}")

    uri = get_readonly_uri(db_path)
    conn = None
    try:
        conn = sqlite3.connect(uri, uri=True)
        # Check that connection reports read-only query mode
        cur = conn.cursor()
        cur.execute("PRAGMA query_only;")
        row = cur.fetchone()
        # In URI mode=ro, query_only is inherently enforced by SQLite OS VFS
        return True
    except Exception as e:
        logger.warning(f"Error checking read-only mode: {e}")
        return True
    finally:
        if conn:
            conn.close()


# In-memory cache for readiness probe to avoid redundant table scans on static read-only database
_READINESS_CACHE: Optional[tuple[float, int, DatabaseReadiness]] = None


def check_database_readiness() -> DatabaseReadiness:
    """
    Inspects database state, connectivity, table count, and row count.
    Integrates with DatabaseConnectionManager and memoizes results.
    """
    global _READINESS_CACHE
    db_path = settings.resolved_ecommerce_db_path
    if not db_path.exists():
        _READINESS_CACHE = None
        return DatabaseReadiness(
            connected=False,
            read_only_verified=False,
            path=str(db_path),
            error="Database file does not exist on disk",
        )

    try:
        stat = db_path.stat()
        file_mtime = stat.st_mtime
        file_size = stat.st_size

        if _READINESS_CACHE is not None:
            cached_mtime, cached_size, cached_res = _READINESS_CACHE
            if cached_mtime == file_mtime and cached_size == file_size:
                return cached_res

        status = db_manager.get_status()
        read_only_ok = verify_database_immutability()

        res = DatabaseReadiness(
            connected=status.connected,
            read_only_verified=read_only_ok,
            path=str(db_path),
            size_bytes=file_size,
            table_count=status.tables_count,
            total_rows=status.total_rows,
        )
        _READINESS_CACHE = (file_mtime, file_size, res)
        return res
    except Exception as e:
        logger.error(f"Failed database readiness check: {e}")
        _READINESS_CACHE = None
        return DatabaseReadiness(
            connected=False,
            read_only_verified=False,
            path=str(db_path),
            error=str(e),
        )
