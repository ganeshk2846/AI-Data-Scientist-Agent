"""
Read-only SQL query executor with timeouts, row bounds, and execution timing.
"""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from backend.app.core.errors import DatabaseError
from backend.app.core.logging import logger
from backend.app.db.connection import get_readonly_connection


class QueryExecutionResult(BaseModel):
    """Structured result from a read-only query execution."""
    sql: str
    columns: List[str]
    rows: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    truncated: bool = False
    error: Optional[str] = None


class SQLExecutor:
    """Executes validated SQL queries against the read-only SQLite database."""

    def execute_query(self, sql_query: str) -> QueryExecutionResult:
        start_time = time.perf_counter()
        with get_readonly_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(sql_query)
                col_names = [d[0] for d in cursor.description] if cursor.description else []

                # Fetch bounded rows
                raw_rows = cursor.fetchmany(settings.SQL_MAX_ROWS_RETURN + 1)
                truncated = len(raw_rows) > settings.SQL_MAX_ROWS_RETURN
                if truncated:
                    raw_rows = raw_rows[:settings.SQL_MAX_ROWS_RETURN]

                formatted_rows = [dict(zip(col_names, row)) for row in raw_rows]
                elapsed_ms = (time.perf_counter() - start_time) * 1000

                return QueryExecutionResult(
                    sql=sql_query,
                    columns=col_names,
                    rows=formatted_rows,
                    row_count=len(formatted_rows),
                    execution_time_ms=round(elapsed_ms, 2),
                    truncated=truncated,
                )
            except Exception as e:
                elapsed_ms = (time.perf_counter() - start_time) * 1000
                logger.error(f"SQL execution failure: {e} | Query: {sql_query}")
                raise DatabaseError(
                    message=f"SQL execution error: {str(e)}",
                    details={"sql": sql_query, "execution_time_ms": round(elapsed_ms, 2)},
                )


sql_executor = SQLExecutor()
