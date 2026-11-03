"""
Observability and run-tracing subsystem for the AI for BI Agent.
Records run traces, stage spans, execution latency, SQL verification statuses, and cost metrics in agent_app.sqlite.
"""

import json
import sqlite3
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from pydantic import BaseModel, Field
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.security.guardrails import redact_sensitive_data


class StageSpanRecord(BaseModel):
    span_id: str
    run_id: str
    stage_name: str
    duration_ms: float
    start_time: str
    end_time: str
    status: str = "completed"
    metadata_json: Optional[str] = None


class StageLatencyMetric(BaseModel):
    p50_ms: float
    p95_ms: float
    avg_ms: float
    count: int


class StreamingTimingMetric(BaseModel):
    ttfe_p50_ms: float = 0.0
    ttfe_p95_ms: float = 0.0
    ttfo_p50_ms: float = 0.0
    ttfo_p95_ms: float = 0.0
    count: int = 0


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
    orchestrator_type: Optional[str] = "agentic_supervisor"
    llm_provider: Optional[str] = "groq"
    llm_calls_count: int = 0
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    streaming_ttfe_ms: Optional[float] = None
    streaming_ttfo_ms: Optional[float] = None


class ObservabilityMetrics(BaseModel):
    total_runs: int
    success_rate_pct: float
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    avg_latency_ms: float
    safety_block_count: int
    error_classes_breakdown: Dict[str, int] = Field(default_factory=dict)
    # High-resolution & stage-level telemetry
    window: str = "all"
    window_sample_count: int = 0
    active_engine: str = "Groq Cloud API"
    verified_runs_count: int = 0
    verified_latency_p50_ms: float = 0.0
    verified_latency_p95_ms: float = 0.0
    verified_latency_p99_ms: float = 0.0
    verified_avg_latency_ms: float = 0.0
    orchestrator_breakdown: Dict[str, int] = Field(default_factory=dict)
    stage_latencies: Dict[str, StageLatencyMetric] = Field(default_factory=dict)
    streaming_timings: Optional[StreamingTimingMetric] = None


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

            # Create ops_stage_spans table for stage-level telemetry
            cur.execute("""
                CREATE TABLE IF NOT EXISTS ops_stage_spans (
                    span_id TEXT PRIMARY KEY,
                    run_id TEXT NOT NULL,
                    stage_name TEXT NOT NULL,
                    duration_ms REAL NOT NULL,
                    start_time TEXT NOT NULL,
                    end_time TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata_json TEXT
                );
            """)
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ops_spans_run ON ops_stage_spans(run_id);")
            cur.execute("CREATE INDEX IF NOT EXISTS idx_ops_spans_stage ON ops_stage_spans(stage_name);")

            # Check and safely add optional columns to ops_run_traces for forward/backward compatibility
            cur.execute("PRAGMA table_info(ops_run_traces);")
            existing_cols = {row["name"] for row in cur.fetchall()}

            cols_to_add = [
                ("orchestrator_type", "TEXT DEFAULT 'agentic_supervisor'"),
                ("llm_provider", "TEXT DEFAULT 'groq'"),
                ("llm_calls_count", "INTEGER DEFAULT 0"),
                ("prompt_tokens", "INTEGER"),
                ("completion_tokens", "INTEGER"),
                ("total_tokens", "INTEGER"),
                ("streaming_ttfe_ms", "REAL"),
                ("streaming_ttfo_ms", "REAL"),
            ]
            for col_name, col_def in cols_to_add:
                if col_name not in existing_cols:
                    cur.execute(f"ALTER TABLE ops_run_traces ADD COLUMN {col_name} {col_def};")

            # Backfill orchestrator_type correctly for all records based on execution ID signature
            cur.execute("""
                UPDATE ops_run_traces
                SET orchestrator_type = CASE
                    WHEN run_id LIKE 'exec_%' THEN 'agentic_supervisor'
                    ELSE 'workflow_orchestrator'
                END;
            """)

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

            orch_type = trace.orchestrator_type
            if not orch_type:
                orch_type = "agentic_supervisor" if trace.run_id.startswith("exec_") else "workflow_orchestrator"

            cur.execute(
                """
                INSERT OR REPLACE INTO ops_run_traces 
                (run_id, session_id, query, intent, latency_ms, sql_executed, row_count, cost_estimate_usd, 
                 error_class, verification_status, created_at, orchestrator_type, llm_provider, 
                 llm_calls_count, prompt_tokens, completion_tokens, total_tokens, streaming_ttfe_ms, streaming_ttfo_ms)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
                    orch_type,
                    trace.llm_provider or "groq",
                    trace.llm_calls_count,
                    trace.prompt_tokens,
                    trace.completion_tokens,
                    trace.total_tokens,
                    round(trace.streaming_ttfe_ms, 2) if trace.streaming_ttfe_ms is not None else None,
                    round(trace.streaming_ttfo_ms, 2) if trace.streaming_ttfo_ms is not None else None,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def update_streaming_timings(self, run_id: str, ttfe_ms: float, ttfo_ms: float) -> None:
        """Update streaming time-to-first-event and time-to-first-output for an execution run."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                UPDATE ops_run_traces
                SET streaming_ttfe_ms = ?, streaming_ttfo_ms = ?
                WHERE run_id = ?
                """,
                (round(ttfe_ms, 2), round(ttfo_ms, 2), run_id),
            )
            conn.commit()
        finally:
            conn.close()

    def record_stage_spans(self, spans: List[StageSpanRecord]) -> None:
        """Persist individual execution stage spans."""
        if not spans:
            return
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.executemany(
                """
                INSERT OR REPLACE INTO ops_stage_spans
                (span_id, run_id, stage_name, duration_ms, start_time, end_time, status, metadata_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        s.span_id,
                        s.run_id,
                        s.stage_name,
                        round(s.duration_ms, 2),
                        s.start_time,
                        s.end_time,
                        s.status,
                        s.metadata_json,
                    )
                    for s in spans
                ],
            )
            conn.commit()
        finally:
            conn.close()

    def get_stage_spans(self, run_id: str) -> List[StageSpanRecord]:
        """Retrieve stage spans for a specific run execution."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT * FROM ops_stage_spans
                WHERE run_id = ?
                ORDER BY start_time ASC
                """,
                (run_id,),
            )
            rows = cur.fetchall()
            return [
                StageSpanRecord(
                    span_id=r["span_id"],
                    run_id=r["run_id"],
                    stage_name=r["stage_name"],
                    duration_ms=r["duration_ms"],
                    start_time=r["start_time"],
                    end_time=r["end_time"],
                    status=r["status"],
                    metadata_json=r["metadata_json"],
                )
                for r in rows
            ]
        finally:
            conn.close()

    def get_recent_traces(self, limit: int = 50) -> List[RunTraceRecord]:
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
                    orchestrator_type=r["orchestrator_type"] if "orchestrator_type" in r.keys() else None,
                    llm_provider=r["llm_provider"] if "llm_provider" in r.keys() else "groq",
                    llm_calls_count=r["llm_calls_count"] if "llm_calls_count" in r.keys() else 0,
                    prompt_tokens=r["prompt_tokens"] if "prompt_tokens" in r.keys() else None,
                    completion_tokens=r["completion_tokens"] if "completion_tokens" in r.keys() else None,
                    total_tokens=r["total_tokens"] if "total_tokens" in r.keys() else None,
                    streaming_ttfe_ms=r["streaming_ttfe_ms"] if "streaming_ttfe_ms" in r.keys() else None,
                    streaming_ttfo_ms=r["streaming_ttfo_ms"] if "streaming_ttfo_ms" in r.keys() else None,
                )
                for r in rows
            ]
        finally:
            conn.close()

    def compute_metrics(
        self,
        window: str = "all",
        orchestrator: str = "all",
        status_filter: str = "all",
    ) -> ObservabilityMetrics:
        """
        Computes accurate non-parametric latency percentiles and system metrics.
        
        Args:
            window: 'all', 'recent_100', 'recent_50', or 'active_groq'
            orchestrator: 'all', 'agentic_supervisor', or 'workflow_orchestrator'
            status_filter: 'all', 'verified', 'refused', 'blocked', or 'abstained'
        """
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            # Build query predicate
            where_clauses: List[str] = []
            params: List[Any] = []

            if orchestrator == "agentic_supervisor":
                where_clauses.append("(orchestrator_type = 'agentic_supervisor' OR run_id LIKE 'exec_%')")
            elif orchestrator == "workflow_orchestrator":
                where_clauses.append("(orchestrator_type = 'workflow_orchestrator' AND run_id NOT LIKE 'exec_%')")

            if status_filter != "all":
                where_clauses.append("verification_status = ?")
                params.append(status_filter)

            if window == "active_groq":
                where_clauses.append("(llm_provider = 'groq' OR created_at >= '2026-11-03T16:00:00')")

            where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

            limit_sql = ""
            if window == "recent_50":
                limit_sql = "LIMIT 50"
            elif window == "recent_100":
                limit_sql = "LIMIT 100"

            query_sql = f"""
                SELECT run_id, latency_ms, verification_status, error_class, orchestrator_type,
                       streaming_ttfe_ms, streaming_ttfo_ms
                FROM ops_run_traces
                {where_sql}
                ORDER BY created_at DESC
                {limit_sql}
            """
            cur.execute(query_sql, params)
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
                    window=window,
                    window_sample_count=0,
                    active_engine="Groq Cloud API (gpt-oss-120b)",
                )

            latencies = [float(r["latency_ms"]) for r in rows]
            total = len(rows)
            success_count = sum(1 for r in rows if r["verification_status"] == "verified")
            safety_blocks = sum(1 for r in rows if r["error_class"] in ["sql_security_block", "prompt_injection_block", "destructive_sql_block"])

            # Verified-only subset for truthful unmasked analytical latency
            verified_latencies = [float(r["latency_ms"]) for r in rows if r["verification_status"] == "verified"]

            error_counts: Dict[str, int] = {}
            orch_counts: Dict[str, int] = {}
            for r in rows:
                ec = r["error_class"]
                if ec:
                    error_counts[ec] = error_counts.get(ec, 0) + 1
                ot = r["orchestrator_type"] or ("agentic_supervisor" if str(r["run_id"]).startswith("exec_") else "workflow_orchestrator")
                orch_counts[ot] = orch_counts.get(ot, 0) + 1

            p50 = float(np.percentile(latencies, 50))
            p95 = float(np.percentile(latencies, 95))
            p99 = float(np.percentile(latencies, 99))
            avg_lat = float(np.mean(latencies))

            v_p50 = float(np.percentile(verified_latencies, 50)) if verified_latencies else 0.0
            v_p95 = float(np.percentile(verified_latencies, 95)) if verified_latencies else 0.0
            v_p99 = float(np.percentile(verified_latencies, 99)) if verified_latencies else 0.0
            v_avg = float(np.mean(verified_latencies)) if verified_latencies else 0.0

            # Streaming timings
            ttfe_vals = [float(r["streaming_ttfe_ms"]) for r in rows if r["streaming_ttfe_ms"] is not None]
            ttfo_vals = [float(r["streaming_ttfo_ms"]) for r in rows if r["streaming_ttfo_ms"] is not None]
            streaming_timings = None
            if ttfe_vals or ttfo_vals:
                streaming_timings = StreamingTimingMetric(
                    ttfe_p50_ms=round(float(np.percentile(ttfe_vals, 50)), 1) if ttfe_vals else 0.0,
                    ttfe_p95_ms=round(float(np.percentile(ttfe_vals, 95)), 1) if ttfe_vals else 0.0,
                    ttfo_p50_ms=round(float(np.percentile(ttfo_vals, 50)), 1) if ttfo_vals else 0.0,
                    ttfo_p95_ms=round(float(np.percentile(ttfo_vals, 95)), 1) if ttfo_vals else 0.0,
                    count=max(len(ttfe_vals), len(ttfo_vals)),
                )

            # Compute stage-level latency metrics from ops_stage_spans
            run_ids = [r["run_id"] for r in rows]
            stage_metrics: Dict[str, StageLatencyMetric] = {}
            if run_ids:
                placeholders = ",".join("?" for _ in run_ids[:500])
                cur.execute(
                    f"""
                    SELECT stage_name, duration_ms
                    FROM ops_stage_spans
                    WHERE run_id IN ({placeholders})
                    """,
                    run_ids[:500],
                )
                span_rows = cur.fetchall()
                stage_groups: Dict[str, List[float]] = {}
                for sr in span_rows:
                    sn = sr["stage_name"]
                    stage_groups.setdefault(sn, []).append(float(sr["duration_ms"]))

                for sname, sdurations in stage_groups.items():
                    if sdurations:
                        stage_metrics[sname] = StageLatencyMetric(
                            p50_ms=round(float(np.percentile(sdurations, 50)), 1),
                            p95_ms=round(float(np.percentile(sdurations, 95)), 1),
                            avg_ms=round(float(np.mean(sdurations)), 1),
                            count=len(sdurations),
                        )

            return ObservabilityMetrics(
                total_runs=total,
                success_rate_pct=round((success_count / total) * 100.0, 1) if total > 0 else 100.0,
                latency_p50_ms=round(p50, 1),
                latency_p95_ms=round(p95, 1),
                latency_p99_ms=round(p99, 1),
                avg_latency_ms=round(avg_lat, 1),
                safety_block_count=safety_blocks,
                error_classes_breakdown=error_counts,
                window=window,
                window_sample_count=total,
                active_engine="Groq Cloud API (gpt-oss-120b)",
                verified_runs_count=len(verified_latencies),
                verified_latency_p50_ms=round(v_p50, 1),
                verified_latency_p95_ms=round(v_p95, 1),
                verified_latency_p99_ms=round(v_p99, 1),
                verified_avg_latency_ms=round(v_avg, 1),
                orchestrator_breakdown=orch_counts,
                stage_latencies=stage_metrics,
                streaming_timings=streaming_timings,
            )
        finally:
            conn.close()


observability_tracer = ObservabilityTracer()
