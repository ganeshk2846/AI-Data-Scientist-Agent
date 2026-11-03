"""
Unit and regression tests for stage-level latency instrumentation, non-parametric percentiles,
windowed telemetry metrics, and streaming SSE timing capture.
"""

import os
import time
import uuid
import pytest
from datetime import datetime, timezone

from backend.app.agents.router import router_agent
from backend.app.observability.tracer import (
    ObservabilityTracer,
    RunTraceRecord,
    StageSpanRecord,
)


@pytest.fixture
def temp_tracer(tmp_path):
    """Provides a fresh isolated tracer SQLite instance for tests."""
    db_file = str(tmp_path / "test_tracer.sqlite")
    tracer = ObservabilityTracer(db_path=db_file)
    return tracer


def test_monotonic_stage_spans_recording(temp_tracer):
    run_id = f"test_run_{uuid.uuid4().hex[:8]}"
    
    # Record top-level trace
    trace = RunTraceRecord(
        run_id=run_id,
        session_id="test_session",
        query="What are total orders?",
        intent="descriptive",
        latency_ms=120.5,
        sql_executed="SELECT count(*) FROM orders",
        row_count=100,
        cost_estimate_usd=0.0002,
        error_class=None,
        verification_status="verified",
        created_at=datetime.now(timezone.utc).isoformat(),
        orchestrator_type="agentic_supervisor",
        llm_provider="groq",
    )
    temp_tracer.record_run_trace(trace)
    
    # Record stage spans
    spans = [
        StageSpanRecord(
            span_id=f"{run_id}_stage_1",
            run_id=run_id,
            stage_name="schema_grounded_sql_extraction",
            duration_ms=45.2,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            status="COMPLETED",
        ),
        StageSpanRecord(
            span_id=f"{run_id}_stage_2",
            run_id=run_id,
            stage_name="factual_faithfulness_and_causal_interception",
            duration_ms=2.1,
            start_time=datetime.now(timezone.utc).isoformat(),
            end_time=datetime.now(timezone.utc).isoformat(),
            status="COMPLETED",
        ),
    ]
    temp_tracer.record_stage_spans(spans)
    
    retrieved = temp_tracer.get_stage_spans(run_id)
    assert len(retrieved) == 2
    assert retrieved[0].stage_name == "schema_grounded_sql_extraction"
    assert retrieved[0].duration_ms == 45.2
    assert retrieved[1].stage_name == "factual_faithfulness_and_causal_interception"
    assert retrieved[1].duration_ms == 2.1


def test_compute_metrics_window_and_orchestrator_filtering(temp_tracer):
    # Insert 10 fast supervisor runs
    for i in range(10):
        temp_tracer.record_run_trace(
            RunTraceRecord(
                run_id=f"exec_sup_{i}",
                session_id="session_sup",
                query=f"supervisor query {i}",
                intent="descriptive",
                latency_ms=30.0 + i * 2.0,  # 30 to 48ms
                verification_status="verified",
                created_at=f"2026-11-03T18:{i:02d}:00+00:00",
                orchestrator_type="agentic_supervisor",
                llm_provider="groq",
            )
        )
    
    # Insert 5 slower workflow runs
    for i in range(5):
        temp_tracer.record_run_trace(
            RunTraceRecord(
                run_id=f"wf_{i}",
                session_id="session_wf",
                query=f"workflow query {i}",
                intent="descriptive",
                latency_ms=2500.0 + i * 100.0,  # 2500 to 2900ms
                verification_status="verified",
                created_at=f"2026-11-03T17:{i:02d}:00+00:00",
                orchestrator_type="workflow_orchestrator",
                llm_provider="groq",
            )
        )
    
    # All metrics
    all_metrics = temp_tracer.compute_metrics(orchestrator="all")
    assert all_metrics.total_runs == 15
    assert all_metrics.latency_p50_ms < 100.0  # Median is in the supervisor group
    
    # Filter supervisor only
    sup_metrics = temp_tracer.compute_metrics(orchestrator="agentic_supervisor")
    assert sup_metrics.total_runs == 10
    assert sup_metrics.latency_p50_ms < 50.0
    assert sup_metrics.latency_p95_ms < 60.0
    
    # Filter workflow only
    wf_metrics = temp_tracer.compute_metrics(orchestrator="workflow_orchestrator")
    assert wf_metrics.total_runs == 5
    assert wf_metrics.latency_p50_ms >= 2500.0


def test_verified_vs_overall_latency_separation(temp_tracer):
    # 5 verified queries with ~500ms
    for i in range(5):
        temp_tracer.record_run_trace(
            RunTraceRecord(
                run_id=f"ver_{i}",
                session_id="sess",
                query=f"query {i}",
                intent="descriptive",
                latency_ms=500.0,
                verification_status="verified",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    
    # 5 security blocked queries with 0ms
    for i in range(5):
        temp_tracer.record_run_trace(
            RunTraceRecord(
                run_id=f"block_{i}",
                session_id="sess",
                query=f"malicious injection {i}",
                intent="security_blocked",
                latency_ms=0.0,
                error_class="prompt_injection_block",
                verification_status="blocked",
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )
    
    metrics = temp_tracer.compute_metrics()
    assert metrics.total_runs == 10
    assert metrics.safety_block_count == 5
    # Overall p50 is pulled down by 0ms
    assert metrics.latency_p50_ms == 250.0
    # Verified-only p50 truthfully reflects actual analytical queries
    assert metrics.verified_runs_count == 5
    assert metrics.verified_latency_p50_ms == 500.0


def test_streaming_timings_update(temp_tracer):
    run_id = f"stream_run_{uuid.uuid4().hex[:8]}"
    temp_tracer.record_run_trace(
        RunTraceRecord(
            run_id=run_id,
            session_id="sess",
            query="Stream test",
            intent="descriptive",
            latency_ms=250.0,
            verification_status="verified",
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    )
    
    temp_tracer.update_streaming_timings(run_id=run_id, ttfe_ms=18.5, ttfo_ms=120.0)
    
    traces = temp_tracer.get_recent_traces(limit=1)
    assert len(traces) == 1
    assert traces[0].streaming_ttfe_ms == 18.5
    assert traces[0].streaming_ttfo_ms == 120.0


def test_router_deterministic_fast_path():
    """Verify deterministic fast path classifies in sub-millisecond without LLM."""
    import asyncio
    t0 = time.perf_counter()
    res = asyncio.run(router_agent.route("What are our total orders?"))
    elapsed_ms = (time.perf_counter() - t0) * 1000
    
    assert res.intent == "descriptive"
    assert res.confidence >= 0.95
    assert elapsed_ms < 50.0  # Fast-path must execute in less than 50ms
