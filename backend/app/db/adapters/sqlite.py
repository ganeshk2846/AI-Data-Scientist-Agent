"""
backend/app/db/adapters/sqlite.py
SQLite connection adapter using SQLAlchemy 2.0 Core and built-in sqlite3.
Enforces strict URI mode=ro and PRAGMA query_only=ON for immutable execution.
"""

from contextlib import contextmanager
import hashlib
from pathlib import Path
import sqlite3
from typing import Any, Dict, Generator, List, Optional
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import NullPool
from backend.app.core.contracts import SupportedEngine
from backend.app.core.errors import DatabaseError, DatabaseReadOnlyViolationError
from backend.app.core.logging import logger
from backend.app.db.base import BaseDatabaseAdapter, QueryResult


class SQLiteAdapter(BaseDatabaseAdapter):
    """Production SQLite adapter with read-only enforcement and connection pooling."""

    def __init__(self, file_path: str | Path, name: Optional[str] = None, read_only: bool = True):
        self.file_path = Path(file_path).resolve()
        super().__init__(name=name or self.file_path.name, read_only=read_only)
        self._engine: Optional[Engine] = None

    @property
    def engine_type(self) -> SupportedEngine:
        return SupportedEngine.SQLITE

    @property
    def uri(self) -> str:
        """Strict URI read-only path."""
        clean_path = self.file_path.as_posix()
        mode = "ro" if self.read_only else "rw"
        return f"file:{clean_path}?mode={mode}"

    def connect(self) -> None:
        """Initializes SQLAlchemy engine with NullPool and attaches read-only hooks."""
        if not self.file_path.exists():
            raise DatabaseError(f"SQLite database file not found at: {self.file_path}")

        try:
            # Custom creator ensures uri=True with mode=ro
            def dbapi_creator():
                con = sqlite3.connect(self.uri, uri=True, timeout=30.0)
                con.row_factory = sqlite3.Row
                return con

            self._engine = create_engine(
                "sqlite://",
                creator=dbapi_creator,
                poolclass=NullPool,
            )

            # Enforce PRAGMA query_only = ON on every connection
            if self.read_only:
                @event.listens_for(self._engine, "connect")
                def set_sqlite_readonly(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    try:
                        cursor.execute("PRAGMA query_only = ON;")
                    except Exception as e:
                        logger.warning(f"Failed to set PRAGMA query_only on SQLite: {e}")
                    finally:
                        cursor.close()

            # Test connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1;"))

            self._connected = True
            logger.info(f"Connected SQLiteAdapter to {self.file_path} (read_only={self.read_only})")

        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect SQLiteAdapter to {self.file_path}: {e}")
            raise DatabaseError(f"Failed to connect to SQLite database: {e}")

    def disconnect(self) -> None:
        """Disposes engine connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        self._connected = False
        logger.info(f"Disconnected SQLiteAdapter from {self.file_path}")

    def _execute_raw(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """Executes query through SQLAlchemy connection."""
        if not self._engine:
            raise DatabaseError("Database is not connected.")

        try:
            with self._engine.connect() as conn:
                if timeout:
                    conn = conn.execution_options(timeout=timeout)

                result = conn.execute(text(sql), params or {})
                columns = list(result.keys()) if result.returns_rows else []
                rows = [dict(zip(columns, row)) for row in result.fetchall()] if result.returns_rows else []
                row_count = len(rows)

                return QueryResult(
                    sql=sql,
                    columns=columns,
                    rows=rows,
                    row_count=row_count,
                    truncated=(row_count >= 1000),
                )
        except sqlite3.OperationalError as e:
            if "readonly" in str(e).lower() or "attempt to write a readonly database" in str(e).lower():
                raise DatabaseReadOnlyViolationError(f"Write operation blocked by SQLite read-only mode: {e}")
            raise DatabaseError(f"SQLite operational error: {e}")
        except Exception as e:
            if "readonly" in str(e).lower() or "attempt to write a readonly database" in str(e).lower():
                raise DatabaseReadOnlyViolationError(f"Write operation blocked by SQLite read-only mode: {e}")
            raise DatabaseError(f"Query execution failed: {e}")

    def get_table_names(self) -> List[str]:
        """Returns non-system table names."""
        if not self._engine:
            self.connect()
        inspector = inspect(self._engine)
        tables = [t for t in inspector.get_table_names() if not t.startswith("sqlite_")]
        return sorted(tables)

    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count of specified table."""
        res = self._execute_raw(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
        if res.rows:
            return int(res.rows[0].get("cnt", 0))
        return 0

    def compute_fingerprint(self) -> str:
        """Computes SHA-256 fingerprint from table names, row counts, and column counts."""
        tables = self.get_table_names()
        tokens = []
        for t in tables:
            cnt = self.get_table_row_count(t)
            tokens.append(f"{t}:{cnt}")
        payload = "|".join(tokens).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @contextmanager
    def raw_connection(self) -> Generator[sqlite3.Connection, None, None]:
        """Context manager yielding raw sqlite3.Connection with Row factory."""
        conn = None
        try:
            conn = sqlite3.connect(self.uri, uri=True, timeout=30.0)
            conn.row_factory = sqlite3.Row
            if self.read_only:
                conn.execute("PRAGMA query_only = ON;")
            yield conn
        finally:
            if conn:
                conn.close()
