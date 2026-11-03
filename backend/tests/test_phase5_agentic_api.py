"""
backend/tests/test_phase5_agentic_api.py
API Endpoint Verification for Phase 5 Agentic Orchestration.

Tests:
1. POST /api/v1/agentic/supervise: Request/response contract, task breakdown, management brief.
2. POST /api/v1/agentic/stream: Server-Sent Events (SSE) streaming progress and result payloads.
"""

from fastapi.testclient import TestClient
from backend.app.main import app

client = TestClient(app)


def test_api_agentic_supervise_endpoint():
    resp = client.post(
        "/api/v1/agentic/supervise",
        json={
            "question": "Describe total sales revenue and orders during the period.",
            "session_id": "test_api_session_1",
        },
    )

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    result = data["data"]
    assert "execution_id" in result
    assert "tasks" in result
    assert len(result["tasks"]) >= 3
    assert "management_response" in result
    assert result["management_response"]["what"] is not None
    assert result["management_response"]["what"]["title"] == "WHAT"


def test_api_agentic_stream_endpoint():
    resp = client.post(
        "/api/v1/agentic/stream",
        json={
            "question": "Why did sales decrease? Explain the drivers.",
            "session_id": "test_api_stream_session",
        },
    )

    assert resp.status_code == 200
    assert "text/event-stream" in resp.headers.get("content-type", "")

    lines = resp.text.split("\n\n")
    events = []
    for block in lines:
        if not block.strip():
            continue
        for line in block.split("\n"):
            if line.startswith("event:"):
                events.append(line.replace("event:", "").strip())

    assert "progress" in events
    assert "result" in events
