"""
REST endpoints for Observability, Telemetry, and Run Traces.
Provides high-resolution latency percentiles, stage span breakdowns, and trace audits.
"""

from typing import List, Optional
from fastapi import APIRouter, Query, Request
from backend.app.core.models import APIResponse
from backend.app.observability.tracer import (
    ObservabilityMetrics,
    RunTraceRecord,
    StageSpanRecord,
    observability_tracer,
)

router = APIRouter(prefix="/ops", tags=["Observability & Telemetry"])


@router.get(
    "/metrics",
    response_model=APIResponse[ObservabilityMetrics],
    summary="Get aggregated latency percentiles and reliability metrics with windowed and orchestrator filters",
)
async def get_metrics(
    request: Request,
    window: str = Query(default="all", description="Telemetry window: 'all', 'recent_100', 'recent_50', 'active_groq'"),
    orchestrator: str = Query(default="all", description="Orchestrator filter: 'all', 'agentic_supervisor', 'workflow_orchestrator'"),
    status: str = Query(default="all", description="Status filter: 'all', 'verified', 'refused', 'blocked', 'abstained'"),
) -> APIResponse[ObservabilityMetrics]:
    request_id = getattr(request.state, "request_id", None)
    metrics = observability_tracer.compute_metrics(
        window=window,
        orchestrator=orchestrator,
        status_filter=status,
    )
    return APIResponse(success=True, data=metrics, request_id=request_id)


@router.get(
    "/traces",
    response_model=APIResponse[List[RunTraceRecord]],
    summary="List recent execution run traces",
)
async def list_traces(
    request: Request,
    limit: int = Query(default=50, ge=1, le=500),
) -> APIResponse[List[RunTraceRecord]]:
    request_id = getattr(request.state, "request_id", None)
    traces = observability_tracer.get_recent_traces(limit=limit)
    return APIResponse(success=True, data=traces, request_id=request_id)


@router.get(
    "/spans/{run_id}",
    response_model=APIResponse[List[StageSpanRecord]],
    summary="Retrieve granular stage-level latency spans for a specific execution run",
)
async def get_run_spans(
    run_id: str,
    request: Request,
) -> APIResponse[List[StageSpanRecord]]:
    request_id = getattr(request.state, "request_id", None)
    spans = observability_tracer.get_stage_spans(run_id=run_id)
    return APIResponse(success=True, data=spans, request_id=request_id)
