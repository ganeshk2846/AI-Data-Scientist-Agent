"""
Tests for Phase 3: Router, Retriever, SQL Runner, and End-to-End Chat Workflow.
"""

import asyncio
import pytest
from backend.app.agents.router import router_agent
from backend.app.retrieval.retriever import schema_grounder
from backend.app.schema.service import schema_service
from backend.app.sql.executor import sql_executor
from backend.app.workflow.service import query_workflow_service


def test_router_agent_classification():
    r1 = asyncio.run(router_agent.route("What was our total revenue in 2024?"))
    assert r1.intent in ["descriptive", "trend"]
    assert r1.confidence > 0.8

    r2 = asyncio.run(router_agent.route("Why did orders drop sharply in the SP region?"))
    assert r2.intent == "diagnostic"

    r3 = asyncio.run(router_agent.route("Forecast monthly order volume for next quarter"))
    assert r3.intent == "predictive"

    r4 = asyncio.run(router_agent.route("Compare VIP vs Occasional customer average order value"))
    assert r4.intent == "comparative"


def test_schema_grounder_retrieval():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()

    t1 = schema_grounder.retrieve_tables("What is our total revenue?", catalog)
    assert "orders" in t1

    t2 = schema_grounder.retrieve_tables("Show top 5 product categories", catalog)
    assert "products" in t2 or "categories" in t2

    t3 = schema_grounder.retrieve_tables("How many customers in each segment?", catalog)
    assert "customers" in t3 or "customer_segments" in t3


def test_sql_executor_runs_real_query():
    result = sql_executor.execute_query(
        "SELECT order_status, COUNT(*) as cnt FROM orders GROUP BY order_status ORDER BY cnt DESC LIMIT 5;"
    )
    assert result.row_count == 2
    assert "order_status" in result.columns
    assert result.execution_time_ms > 0
    statuses = [r["order_status"] for r in result.rows]
    assert "delivered" in statuses
    assert "cancelled" in statuses


def test_end_to_end_query_workflow():
    result = asyncio.run(query_workflow_service.run_query("Show orders by status and total revenue"))
    assert result.sanitized_sql is not None
    assert result.query_result is not None
    assert result.query_result.row_count > 0
    assert result.composed_answer is not None
    assert len(result.composed_answer) > 10

    # Verify all progress states exist in trace steps
    step_names = [t.step for t in result.trace_steps]
    assert "understanding_question" in step_names
    assert "retrieving_schema" in step_names
    assert "validating_query" in step_names
    assert "running_query" in step_names
    assert "verifying_results" in step_names
    assert "composing_answer" in step_names


def test_chat_query_endpoint(client):
    res = client.post("/api/v1/chat/query", json={"query": "What is our total sales by order status?"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "run_id" in data
    assert "sanitized_sql" in data
    assert data["query_result"] is not None
    assert data["query_result"]["row_count"] > 0
    assert "composed_answer" in data


def test_gemini_provider_instantiation():
    from backend.app.llm.client import GeminiProvider
    provider = GeminiProvider(api_key="AIzaSyTestMockKey", model="gemini-3.5-flash-lite")
    assert provider.model == "gemini-3.5-flash-lite"
    assert provider.client is not None


