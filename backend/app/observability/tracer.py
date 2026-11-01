"""
Observability and run-tracing subsystem for the AI for BI Agent.
Records run traces, execution latency, SQL verification statuses, and cost metrics in agent_app.sqlite.
"""

import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.security.guardrails import redact_sensitive_data


class RunTraceRecord(BaseModel):
    run_id: str
    session_id: str = "default_session"
    query: str
    intent: str
    latency_ms: float
    sql_executed: Optional[str] = None
    row_count: int = 0
    cost_estimate_usd: float = 0.0002
    error_class: Optional[str] = None
    verification_status: str = "verified"
    created_at: str


class ObservabilityMetrics(BaseModel):
    total_runs: int
    success_rate_pct: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    avg_latency_ms: float
    safety_block_count: int
    error_classes_breakdown: Dict[str, int] = Field(default_factory=dict)


class ObservabilityTracer:
    """Manages recording and querying execution telemetry in the application store."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.APP_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ops_run_traces (
                    run_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    query TEXT NOT NULL,
                    intent TEXT NOT NULL,
                    latency_ms REAL NOT NULL,
                    sql_executed TEXT,
                    row_count INTEGER NOT NULL,
                    cost_estimate_usd REAL NOT NULL,
                    error_class TEXT,
                    verification_status TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ops_traces_created ON ops_run_traces(created_at);")
            conn.commit()
        finally:
            conn.close()

    def record_run_trace(self, trace: RunTraceRecord) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            # Apply security redaction to query and SQL before storing telemetry
            safe_query = redact_sensitive_data(trace.query)
            safe_sql = redact_sensitive_data(trace.sql_executed) if trace.sql_executed else None

            cur.execute(
                """
                INSERT OR REPLACE INTO ops_run_traces 
                (run_id, session_id, query, intent, latency_ms, sql_executed, row_count, cost_estimate_usd, error_class, verification_status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    trace.run_id,
                    trace.session_id,
                    safe_query,
                    trace.intent,
                    round(trace.latency_ms, 2),
                    safe_sql,
                    trace.row_count,
                    trace.cost_estimate_usd,
                    trace.error_class,
                    trace.verification_status,
                    trace.created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_traces(self, limit: int = 25) -> List[RunTraceRecord]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT * FROM ops_run_traces 
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (limit,),
            )
            rows = cur.fetchall()
            return [
                RunTraceRecord(
                    run_id=r["run_id"],
                    session_id=r["session_id"],
                    query=r["query"],
                    intent=r["intent"],
                    latency_ms=r["latency_ms"],
                    sql_executed=r["sql_executed"],
                    row_count=r["row_count"],
                    cost_estimate_usd=r["cost_estimate_usd"],
                    error_class=r["error_class"],
                    verification_status=r["verification_status"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def compute_metrics(self) -> ObservabilityMetrics:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT latency_ms, verification_status, error_class FROM ops_run_traces")
            rows = cur.fetchall()
            if not rows:
                return ObservabilityMetrics(
                    total_runs=0,
                    success_rate_pct=100.0,
                    latency_p50_ms=0.0,
                    latency_p95_ms=0.0,
                    latency_p99_ms=0.0,
                    avg_latency_ms=0.0,
                    safety_block_count=0,
                    error_classes_breakdown={},
                )

            latencies = [r["latency_ms"] for r in rows]
            total = len(rows)
            success_count = sum(1 for r in rows if r["verification_status"] == "verified")
            safety_blocks = sum(1 for r in rows if r["error_class"] in ["sql_security_block", "prompt_injection_block"])

            error_counts: Dict[str, int] = {}
            for r in rows:
                ec = r["error_class"]
                if ec:
                    error_counts[ec] = error_counts.get(ec, 0) + 1

            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))
            avg_lat = float(np.mean(latencies))

            return ObservabilityMetrics(
                total_runs=total,
                success_rate_pct=round((success_count / total) * 100.0, 1),
                latency_p50_ms=round(p50, 1),
                latency_p95_ms=round(p95, 1),
                latency_p99_ms=round(p99, 1),
                avg_latency_ms=round(avg_lat, 1),
                safety_block_count=safety_blocks,
                error_classes_breakdown=error_counts,
            )
        finally:
            conn.close()


observability_tracer = ObservabilityTracer()

