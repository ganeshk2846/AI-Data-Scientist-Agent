"""
backend/app/db/adapters/postgres.py
PostgreSQL connection adapter using SQLAlchemy 2.0 Core and psycopg v3.
Enforces QueuePool pooling and SET TRANSACTION READ ONLY on connection checkout.
"""

import hashlib
from typing import Any, Dict, List, Optional
from sqlalchemy import create_engine, event, inspect, text
from sqlalchemy.engine import Engine
from sqlalchemy.pool import QueuePool
from backend.app.core.contracts import SupportedEngine
from backend.app.core.errors import DatabaseError, DatabaseReadOnlyViolationError
from backend.app.core.logging import logger
from backend.app.db.base import BaseDatabaseAdapter, QueryResult


class PostgresAdapter(BaseDatabaseAdapter):
    """Production PostgreSQL adapter with psycopg v3 and QueuePool pooling."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 5432,
        database: str = "postgres",
        username: str = "postgres",
        password: Optional[str] = None,
        name: Optional[str] = None,
        read_only: bool = True,
    ):
        super().__init__(name=name or f"postgres://{host}:{port}/{database}", read_only=read_only)
        self.host = host
        self.port = port
        self.database = database
        self.username = username
        self.password = password
        self._engine: Optional[Engine] = None

    @property
    def engine_type(self) -> SupportedEngine:
        return SupportedEngine.POSTGRESQL

    def _build_url(self) -> str:
        """Constructs SQLAlchemy connection URL using psycopg v3 dialect."""
        pwd_part = f":{self.password}" if self.password else ""
        return f"postgresql+psycopg://{self.username}{pwd_part}@{self.host}:{self.port}/{self.database}"

    def connect(self) -> None:
        """Initializes SQLAlchemy engine with QueuePool and read-only checkout hooks."""
        try:
            url = self._build_url()
            self._engine = create_engine(
                url,
                poolclass=QueuePool,
                pool_size=3,
                max_overflow=2,
                pool_recycle=1800,
                pool_pre_ping=True,
            )

            # Enforce read-only session and statement timeouts
            if self.read_only:
                @event.listens_for(self._engine, "connect")
                def set_postgres_readonly(dbapi_connection, connection_record):
                    cursor = dbapi_connection.cursor()
                    try:
                        cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY;")
                        cursor.execute("SET statement_timeout = '30000';")
                    except Exception as e:
                        logger.warning(f"Failed to set Postgres read-only characteristics: {e}")
                    finally:
                        cursor.close()

            # Verify connection
            with self._engine.connect() as conn:
                conn.execute(text("SELECT 1;"))

            self._connected = True
            logger.info(f"Connected PostgresAdapter to {self.name} (read_only={self.read_only})")

        except Exception as e:
            self._connected = False
            logger.error(f"Failed to connect PostgresAdapter to {self.name}: {e}")
            raise DatabaseError(f"Failed to connect to PostgreSQL database: {e}")

    def disconnect(self) -> None:
        """Disposes engine connection pool."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        self._connected = False
        logger.info(f"Disconnected PostgresAdapter from {self.name}")

    def _execute_raw(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """Executes query through pooled SQLAlchemy connection."""
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
        except Exception as e:
            err_msg = str(e).lower()
            if "read-only transaction" in err_msg or "cannot execute" in err_msg:
                raise DatabaseReadOnlyViolationError(f"Write operation blocked by PostgreSQL read-only transaction: {e}")
            raise DatabaseError(f"PostgreSQL query execution failed: {e}")

    def get_table_names(self) -> List[str]:
        """Returns public schema table names."""
        if not self._engine:
            self.connect()
        inspector = inspect(self._engine)
        tables = [t for t in inspector.get_table_names(schema="public")]
        return sorted(tables)

    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count of specified table."""
        res = self._execute_raw(f'SELECT COUNT(*) as cnt FROM "{table_name}"')
        if res.rows:
            return int(res.rows[0].get("cnt", 0))
        return 0

    def compute_fingerprint(self) -> str:
        """Computes SHA-256 fingerprint from table names and row counts."""
        tables = self.get_table_names()
        tokens = [f"{t}:{self.get_table_row_count(t)}" for t in tables]
        payload = "|".join(tokens).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
