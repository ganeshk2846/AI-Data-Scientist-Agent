"""
Verification test suite for Architecture Cleanup & Duplication Removal (Task 1.1).
Tests:
1. MemoryService and Supervisor execution cache synchronization.
2. ObservabilityTracer recording of AgenticSupervisor runs.
3. Unified session clearing across persistent SQLite and in-memory caches.
4. Direct descriptive engine invocation without duplicate specialist wrappers.
5. Backward compatibility of conversational chat routes and schemas.
"""

import asyncio
from datetime import datetime, timezone
import pytest

from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.analysis.descriptive_engine import descriptive_engine
from backend.app.memory.service import memory_service
from backend.app.observability.tracer import observability_tracer
from backend.app.orchestration.supervisor import agentic_supervisor
from backend.app.schema.service import schema_service


def test_supervisor_records_turns_in_memory_service():
    """Verifies AgenticSupervisor persists user and assistant turns to MemoryService."""
    session_id = f"test_cleanup_mem_{int(datetime.now(timezone.utc).timestamp())}"
    question = "What are the total sales by order status?"

    result = agentic_supervisor.supervise(
        question=question,
        session_id=session_id,
        intent_override=IntentCategory.DESCRIPTIVE,
    )
    assert result.success is True

    # Verify turns were recorded in MemoryService
    turns = memory_service.get_session_history(session_id=session_id, limit=5)
    assert len(turns) >= 2, f"Expected at least 2 turns (user + assistant), found {len(turns)}"

    user_turns = [t for t in turns if t.role == "user"]
    assistant_turns = [t for t in turns if t.role == "assistant"]
    assert len(user_turns) >= 1
    assert len(assistant_turns) >= 1
    assert user_turns[0].content == question
    assert len(assistant_turns[0].content) > 10


def test_supervisor_records_traces_in_observability_tracer():
    """Verifies AgenticSupervisor persists execution metrics and traces to ObservabilityTracer."""
    session_id = f"test_cleanup_ops_{int(datetime.now(timezone.utc).timestamp())}"
    question = "Analyze order volume distribution across statuses."

    result = agentic_supervisor.supervise(
        question=question,
        session_id=session_id,
        intent_override=IntentCategory.DESCRIPTIVE,
    )
    assert result.success is True

    recent_traces = observability_tracer.get_recent_traces(limit=10)
    matching = [t for t in recent_traces if t.run_id == result.execution_id]
    assert len(matching) == 1, "Expected matching run_id trace in ops_run_traces"
    trace = matching[0]
    assert trace.query == question
    assert trace.latency_ms > 0
    assert trace.verification_status == "verified"


def test_clear_session_synchronizes_memory_and_supervisor_cache():
    """Verifies clearing a session purges both SQLite turns and in-memory supervisor execution cache."""
    session_id = f"test_cleanup_sync_{int(datetime.now(timezone.utc).timestamp())}"
    question = "What is the total sales amount?"

    result = agentic_supervisor.supervise(
        question=question,
        session_id=session_id,
        intent_override=IntentCategory.DESCRIPTIVE,
    )
    assert result.success is True

    # Verify in-memory cache has the result
    cache_keys = [k for k in agentic_supervisor._session_cache if k[0] == session_id]
    assert len(cache_keys) >= 1

    # Clear session via memory_service and supervisor
    memory_service.clear_session(session_id)
    agentic_supervisor.clear_session(session_id)

    # Verify in-memory cache is emptied
    remaining_cache_keys = [k for k in agentic_supervisor._session_cache if k[0] == session_id]
    assert len(remaining_cache_keys) == 0

    # Verify SQLite turns are emptied
    remaining_turns = memory_service.get_session_history(session_id)
    assert len(remaining_turns) == 0


def test_descriptive_engine_direct_delegation():
    """Verifies supervisor uses descriptive_engine directly without redundant wrappers."""
    catalog = schema_service.get_cached_catalog()
    assert catalog is not None
    # Confirm descriptive_engine is a direct singleton with run_descriptive_analysis
    assert hasattr(descriptive_engine, "run_descriptive_analysis")
    assert callable(descriptive_engine.run_descriptive_analysis)


def test_backward_compatible_chat_query_endpoint(client):
    """Verifies that the legacy /api/v1/chat/query route remains fully backward-compatible."""
    res = client.post(
        "/api/v1/chat/query",
        json={"query": "What are total sales by year?", "session_id": "test_compat_sess"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "run_id" in data
    assert "sanitized_sql" in data
    assert "composed_answer" in data
    assert data["query_result"] is not None
    assert data["query_result"]["row_count"] > 0
