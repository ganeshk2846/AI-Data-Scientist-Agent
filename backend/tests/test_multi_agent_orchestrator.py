"""
Tests for Phase 4: Multi-Agent Planning, Clarification, Answerability Gate, Visualization, and Bounded Repair.
"""

import asyncio
import pytest
from backend.app.agents.clarification import answerability_gate, clarification_agent
from backend.app.agents.contracts import ChartType
from backend.app.agents.planner import planner_agent
from backend.app.agents.router import RouteResult, router_agent
from backend.app.agents.visualization import visualization_agent
from backend.app.schema.service import schema_service
from backend.app.sql.executor import QueryExecutionResult
from backend.app.sql.repair import sql_repair_loop
from backend.app.workflow.orchestrator import multi_agent_orchestrator


def test_answerability_gate_unsupported_domain():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    route = RouteResult(intent="descriptive", confidence=0.9, reasoning="test")

    assessment = answerability_gate.evaluate("What is the current bitcoin price?", route, catalog)
    assert assessment.is_answerable is False
    assert "bitcoin" in assessment.refusal_reason.lower()
    assert len(assessment.available_alternatives) > 0


def test_answerability_gate_temporal_boundary():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    route = RouteResult(intent="descriptive", confidence=0.9, reasoning="test")

    assessment = answerability_gate.evaluate("What was our sales in 2018?", route, catalog)
    assert assessment.is_answerable is False
    assert "2018" in assessment.refusal_reason


def test_clarification_agent_detects_ambiguity():
    route = RouteResult(intent="comparative", confidence=0.85, reasoning="compare")
    res = clarification_agent.check_ambiguity("compare revenue", route)
    assert res.needs_clarification is True
    assert "How would you like to compare revenue?" in res.question
    assert len(res.options) >= 2


def test_planner_agent_creates_dag():
    route = RouteResult(intent="trend", confidence=0.95, reasoning="trend")
    plan = planner_agent.create_plan("Monthly orders in 2024", route, ["orders"])
    assert len(plan.steps) == 7
    step_ids = [s.step_id for s in plan.steps]
    assert "step_1_grounding" in step_ids
    assert "step_4_sql_execution" in step_ids
    assert "step_6_visualization" in step_ids


def test_visualization_agent_specs():
    route_trend = RouteResult(intent="trend", confidence=0.9, reasoning="")
    q_result_trend = QueryExecutionResult(
        sql="SELECT strftime('%Y-%m', order_date) as month, SUM(total_amount) as total_revenue FROM orders GROUP BY month;",
        columns=["month", "total_revenue"],
        rows=[{"month": "2024-01", "total_revenue": 1000.0}],
        row_count=1,
        execution_time_ms=5.0,
    )
    spec_trend = visualization_agent.derive_chart_specification("Monthly trend", route_trend, q_result_trend)
    assert spec_trend.chart_type == ChartType.LINE
    assert spec_trend.x_axis_field == "month"
    assert spec_trend.y_axis_field == "total_revenue"

    # Category Bar Chart
    route_bar = RouteResult(intent="descriptive", confidence=0.9, reasoning="")
    q_result_bar = QueryExecutionResult(
        sql="SELECT order_status, COUNT(*) as order_count FROM orders GROUP BY order_status;",
        columns=["order_status", "order_count"],
        rows=[{"order_status": "delivered", "order_count": 100}],
        row_count=1,
        execution_time_ms=5.0,
    )
    spec_bar = visualization_agent.derive_chart_specification("Orders by status", route_bar, q_result_bar)
    assert spec_bar.chart_type == ChartType.BAR
    assert spec_bar.x_axis_field == "order_status"


def test_bounded_repair_loop_execution():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    failing_sql = "SELECT order_status, invalid_column_name FROM orders;"
    attempt = asyncio.run(
        sql_repair_loop.attempt_repair(
            query="Show orders by status",
            failing_sql=failing_sql,
            error_message="no such column: invalid_column_name",
            schema_context=catalog.to_minimal_prompt_schema(["orders"]),
            catalog=catalog,
            attempt_number=1,
        )
    )
    assert attempt.attempt_number == 1
    assert attempt.validation_passed is True
    assert "invalid_column_name" not in attempt.repaired_sql


def test_end_to_end_orchestrator():
    res = asyncio.run(multi_agent_orchestrator.run("What was our monthly revenue in 2024?"))
    assert res.run_id is not None
    assert res.answerability.is_answerable is True
    assert res.plan is not None
    assert len(res.plan.steps) == 7
    assert res.sanitized_sql is not None
    assert res.query_result is not None
    assert res.query_result.row_count > 0
    assert res.chart_spec is not None
    assert res.chart_spec.chart_type in [ChartType.LINE, ChartType.BAR]
    assert len(res.composed_answer) > 20


def test_api_multi_agent_chat_endpoint(client):
    res = client.post("/api/v1/chat/query", json={"query": "Show orders by status and total revenue"})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "plan" in data
    assert "chart_spec" in data
    assert data["chart_spec"]["chart_type"] in ["bar", "line", "pie", "table"]
    assert "trace_steps" in data
    assert len(data["trace_steps"]) >= 6
