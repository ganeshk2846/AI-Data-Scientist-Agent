"""
backend/app/api/v1/endpoints/agentic.py
FastAPI Endpoints for Phase 5: Agentic Multi-Agent Orchestration & Business Decision Support.

Exposes:
- POST /api/v1/agentic/supervise: Synchronous supervisor execution with task breakdown and management brief.
- POST /api/v1/agentic/stream: Real-time Server-Sent Events (SSE) streaming of agent task status changes and final result.
"""

import asyncio
import json
import time
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.core.models import APIResponse
from backend.app.observability.tracer import observability_tracer
from backend.app.orchestration.models import SupervisorExecutionResult
from backend.app.orchestration.supervisor import agentic_supervisor
from backend.app.schema.service import schema_service

router = APIRouter(prefix="/agentic", tags=["Agentic Orchestration & Decision Support"])


class SuperviseRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1500, description="Business question for the Data Scientist Agent")
    session_id: Optional[str] = Field(default=None, description="Conversational context session identifier")
    intent_override: Optional[IntentCategory] = Field(default=None, description="Optional manual override for primary analytical intent")


@router.post(
    "/supervise",
    response_model=APIResponse[SupervisorExecutionResult],
    summary="Execute multi-agent analytical orchestration and generate executive management brief",
)
async def supervise_query(
    body: SuperviseRequest,
    request: Request,
) -> APIResponse[SupervisorExecutionResult]:
    """
    Executes the Agentic Supervisor workflow:
    1. Schema & Hybrid Retrieval
    2. Analytical Planning & Task Routing (Descriptive, Diagnostic, Predictive, Prescriptive)
    3. Specialist Execution with Evidence Extraction
    4. Critic Validation & Causal Interception
    5. Executive What/Why/What Next/So What Management Synthesis
    """
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog()

    result = agentic_supervisor.supervise(
        question=body.question,
        session_id=body.session_id,
        catalog=catalog,
        intent_override=body.intent_override,
    )

    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.post(
    "/stream",
    summary="Stream agentic orchestration progress states and task execution events via SSE",
)
async def stream_agentic_query(
    body: SuperviseRequest,
    request: Request,
) -> EventSourceResponse:
    """
    Server-Sent Events (SSE) stream providing real-time visibility into specialist task executions
    and delivering the final executive management response with high-resolution streaming latency instrumentation.
    """
    request_id = getattr(request.state, "request_id", None)
    stream_start = time.perf_counter()

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Emit initial planning event (Time to First Event - TTFE)
        ttfe_ms = round((time.perf_counter() - stream_start) * 1000, 2)
        yield {
            "event": "progress",
            "data": json.dumps({
                "type": "planning",
                "message": f"Supervisor analyzing business question: '{body.question[:80]}...'",
                "streaming_ttfe_ms": ttfe_ms,
            }),
        }
        await asyncio.sleep(0.05)

        # Run supervisor execution in threadpool to avoid blocking async loop
        loop = asyncio.get_running_loop()
        catalog = schema_service.get_cached_catalog()
        result: SupervisorExecutionResult = await loop.run_in_executor(
            None,
            lambda: agentic_supervisor.supervise(
                question=body.question,
                session_id=body.session_id,
                catalog=catalog,
                intent_override=body.intent_override,
            ),
        )

        ttfo_ms = round((time.perf_counter() - stream_start) * 1000, 2)

        # Record streaming latency metrics into telemetry store
        try:
            observability_tracer.update_streaming_timings(
                run_id=result.execution_id,
                ttfe_ms=ttfe_ms,
                ttfo_ms=ttfo_ms,
            )
        except Exception:
            pass

        # Emit task progress updates
        for task in result.tasks:
            yield {
                "event": "task_progress",
                "data": json.dumps({
                    "task_id": task.task_id,
                    "specialist": task.specialist.value,
                    "task_type": task.task_type,
                    "status": task.status.value,
                    "duration_ms": task.duration_ms,
                    "output_summary": task.output_summary,
                }),
            }
            await asyncio.sleep(0.02)

        # Emit final completed result with streaming telemetry metadata
        augmented_metrics = dict(result.metrics)
        augmented_metrics["streaming_ttfe_ms"] = ttfe_ms
        augmented_metrics["streaming_ttfo_ms"] = ttfo_ms
        augmented_metrics["streaming_total_ms"] = round((time.perf_counter() - stream_start) * 1000, 2)

        yield {
            "event": "result",
            "data": json.dumps({
                "success": result.success,
                "execution_id": result.execution_id,
                "plan_summary": result.plan_summary,
                "management_response": result.management_response.model_dump(),
                "metrics": augmented_metrics,
                "tasks": [t.model_dump() for t in result.tasks],
            }),
        }

    return EventSourceResponse(event_generator())
