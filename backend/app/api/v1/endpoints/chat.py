"""
Chat and Natural Language Query API endpoints.
Provides standard REST and Server-Sent Events (SSE) streaming for real-time progress updates.
Powered by Multi-Agent Planning, Clarification, and Bounded Repair Orchestrator.
"""

import asyncio
import json
from typing import AsyncGenerator, Optional
from fastapi import APIRouter, Request, status
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from backend.app.core.models import APIResponse
from backend.app.workflow.models import WorkflowProgressState
from backend.app.workflow.orchestrator import MultiAgentWorkflowResult, multi_agent_orchestrator

router = APIRouter(prefix="/chat", tags=["Conversational BI & Multi-Agent Chat"])


class ChatQueryRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=1000, description="User's natural language question")
    session_id: Optional[str] = None


@router.post(
    "/query",
    response_model=APIResponse[MultiAgentWorkflowResult],
    summary="Execute multi-agent business question workflow",
)
async def execute_chat_query(
    body: ChatQueryRequest,
    request: Request,
) -> APIResponse[MultiAgentWorkflowResult]:
    """
    Executes the multi-agent pipeline:
    Router -> Answerability Gate -> Clarification -> Planner DAG -> Grounder -> Validator/Repair -> Executor -> Verifier -> Visualization -> Composer.
    """
    request_id = getattr(request.state, "request_id", None)
    result = await multi_agent_orchestrator.run(body.query, request_id=request_id)
    return APIResponse(success=True, data=result, request_id=request_id)


@router.post(
    "/stream",
    summary="Stream question execution with Server-Sent Events (SSE)",
)
async def stream_chat_query(
    body: ChatQueryRequest,
    request: Request,
) -> EventSourceResponse:
    """
    Streams observable progress states and decision summaries via SSE.
    Events: 'progress', 'result', 'error'.
    """
    request_id = getattr(request.state, "request_id", None)
    queue: asyncio.Queue = asyncio.Queue()

    def sync_progress_callback(step: WorkflowProgressState, msg: str):
        queue.put_nowait({"type": "progress", "step": step, "message": msg})

    async def workflow_task():
        try:
            result = await multi_agent_orchestrator.run(
                body.query,
                request_id=request_id,
                progress_callback=sync_progress_callback,
            )
            await queue.put({"type": "result", "payload": result.model_dump(mode="json")})
        except Exception as e:
            await queue.put({"type": "error", "message": str(e)})
        finally:
            await queue.put(None)  # Sentinel to terminate stream

    asyncio.create_task(workflow_task())

    async def event_generator() -> AsyncGenerator[dict, None]:
        while True:
            if await request.is_disconnected():
                break

            item = await queue.get()
            if item is None:
                yield {"event": "done", "data": json.dumps({"status": "completed"})}
                break

            if item["type"] == "progress":
                yield {
                    "event": "progress",
                    "data": json.dumps({"step": item["step"], "message": item["message"]}),
                }
            elif item["type"] == "result":
                yield {"event": "result", "data": json.dumps(item["payload"])}
            elif item["type"] == "error":
                yield {"event": "error", "data": json.dumps({"error": item["message"]})}

    return EventSourceResponse(event_generator())
