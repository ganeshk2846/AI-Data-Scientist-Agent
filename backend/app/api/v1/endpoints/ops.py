"""
REST endpoints for Observability, Telemetry, and Run Traces.
"""

from typing import List
from fastapi import APIRouter, Request
from backend.app.core.models import APIResponse
from backend.app.observability.tracer import (
    ObservabilityMetrics,
    RunTraceRecord,
    observability_tracer,
)

router = APIRouter(prefix="/ops", tags=["Observability & Telemetry"])


@router.get(
    "/metrics",
    response_model=APIResponse[ObservabilityMetrics],
    summary="Get aggregated latency percentiles and reliability metrics",
)
async def get_metrics(request: Request) -> APIResponse[ObservabilityMetrics]:
    request_id = getattr(request.state, "request_id", None)
    metrics = observability_tracer.compute_metrics()
    return APIResponse(success=True, data=metrics, request_id=request_id)


@router.get(
    "/traces",
    response_model=APIResponse[List[RunTraceRecord]],
    summary="List recent execution run traces",
)
async def list_traces(request: Request, limit: int = 25) -> APIResponse[List[RunTraceRecord]]:
    request_id = getattr(request.state, "request_id", None)
    traces = observability_tracer.get_recent_traces(limit=limit)
    return APIResponse(success=True, data=traces, request_id=request_id)
