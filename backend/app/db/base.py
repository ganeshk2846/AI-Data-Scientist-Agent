"""
backend/app/db/base.py
Base abstractions for multi-engine database adapters.
Enforces uniform execution interface, connection pooling, and safe read-only guarantees.
"""

from abc import ABC, abstractmethod
import re
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.contracts import SupportedEngine
from backend.app.core.errors import DatabaseError, DatabaseReadOnlyViolationError
from backend.app.core.logging import logger
from backend.app.security.guardrails import validate_sql_security


class QueryResult(BaseModel):
    """Normalized query execution result."""
    sql: str
    columns: List[str] = Field(default_factory=list)
    rows: List[Dict[str, Any]] = Field(default_factory=list)
    row_count: int = 0
    execution_time_ms: float = 0.0
    truncated: bool = False
    error: Optional[str] = None


class BaseDatabaseAdapter(ABC):
    """Abstract base class for engine-specific database adapters."""

    def __init__(self, name: str, read_only: bool = True):
        self.name = name
        self.read_only = read_only
        self._connected = False

    @property
    @abstractmethod
    def engine_type(self) -> SupportedEngine:
        """Returns the supported database engine type."""
        pass

    @property
    def is_connected(self) -> bool:
        """Returns True if the adapter has an active connection pool."""
        return self._connected

    @abstractmethod
    def connect(self) -> None:
        """Initializes the connection pool and verifies database readiness."""
        pass

    @abstractmethod
    def disconnect(self) -> None:
        """Disposes the connection pool and releases all database connections."""
        pass

    @abstractmethod
    def _execute_raw(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """Engine-specific execution implementation."""
        pass

    def execute_query(
        self,
        sql: str,
        params: Optional[Dict[str, Any]] = None,
        timeout: Optional[int] = None,
    ) -> QueryResult:
        """
        Executes a query with defense-in-depth safety checks:
        1. Validates AST to block non-SELECT statements and injection vectors.
        2. Injects LIMIT 1000 if not present to avoid memory exhaustion.
        3. Executes query via engine-specific driver with timeout.
        """
        if not self._connected:
            self.connect()

        clean_sql = sql.strip().rstrip(";")

        # Tier 3: AST / Keyword security validation
        is_safe, reason = validate_sql_security(clean_sql)
        if not is_safe:
            logger.warning(f"Rejected unsafe query on {self.name}: {reason} | SQL: {clean_sql[:100]}")
            raise DatabaseReadOnlyViolationError(f"Query rejected by security guardrail: {reason}")

        # Tier 4: Automatic LIMIT enforcement if none provided
        bounded_sql = self._apply_row_limit(clean_sql, max_rows=1000)

        t0 = time.perf_counter()
        res = self._execute_raw(bounded_sql, params=params, timeout=timeout)
        dur = (time.perf_counter() - t0) * 1000
        res.execution_time_ms = round(dur, 2)
        return res

    def _apply_row_limit(self, sql: str, max_rows: int = 1000) -> str:
        """Appends a LIMIT clause if the query does not already specify one."""
        # Check if query already has a LIMIT clause
        if re.search(r"\bLIMIT\s+\d+", sql, re.IGNORECASE):
            return sql
        return f"{sql} LIMIT {max_rows}"

    @abstractmethod
    def get_table_names(self) -> List[str]:
        """Returns all user table names in the active database."""
        pass

    @abstractmethod
    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count for a specific table."""
        pass

    @abstractmethod
    def compute_fingerprint(self) -> str:
        """Returns SHA-256 fingerprint representing active database structure."""
        pass
