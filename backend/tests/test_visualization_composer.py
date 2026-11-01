"""
Unit tests for Phase 7 Visualization Agent and Composer.
Tests Plotly chart specification derivation, field validation, table fallbacks,
and executive answer synthesis with analytical follow-ups.
"""

import pytest
from backend.app.agents.contracts import ChartType
from backend.app.agents.router import RouteResult
from backend.app.agents.visualization import visualization_agent
from backend.app.sql.executor import QueryExecutionResult


def test_visualization_line_chart_for_time_series():
    rows = [
        {"order_date": "2024-01-01", "revenue": 12500.50},
        {"order_date": "2024-01-02", "revenue": 14200.75},
        {"order_date": "2024-01-03", "revenue": 11800.00},
    ]
    exec_result = QueryExecutionResult(
        sql="SELECT order_date, SUM(total_amount) as revenue FROM orders GROUP BY order_date",
        columns=["order_date", "revenue"],
        rows=rows,
        row_count=len(rows),
        execution_time_ms=5.0,
    )
    route = RouteResult(intent="trend", confidence=0.95, reasoning="Time-series query")
    spec = visualization_agent.derive_chart_specification("What is the sales trend?", route, exec_result)

    assert spec.chart_type == ChartType.LINE
    assert spec.fallback_to_table is False
    assert spec.x_axis_field == "order_date"
    assert spec.y_axis_field == "revenue"
    assert len(spec.plotly_data) == 1
    assert spec.plotly_data[0]["type"] == "scatter"
    assert spec.plotly_data[0]["x"] == ["2024-01-01", "2024-01-02", "2024-01-03"]
    assert spec.plotly_data[0]["y"] == [12500.50, 14200.75, 11800.00]


def test_visualization_bar_chart_for_categories():
    rows = [
        {"category_name": "Electronics", "sales": 85000.0},
        {"category_name": "Apparel", "sales": 62000.0},
        {"category_name": "Home & Kitchen", "sales": 41000.0},
        {"category_name": "Books", "sales": 15000.0},
    ]
    exec_result = QueryExecutionResult(
        sql="SELECT category_name, SUM(total_amount) as sales FROM products GROUP BY category_name",
        columns=["category_name", "sales"],
        rows=rows,
        row_count=len(rows),
        execution_time_ms=6.0,
    )
    route = RouteResult(intent="comparative", confidence=0.90, reasoning="Category ranking")
    spec = visualization_agent.derive_chart_specification("Top categories by sales", route, exec_result)

    assert spec.chart_type == ChartType.BAR
    assert spec.fallback_to_table is False
    assert spec.x_axis_field == "category_name"
    assert spec.y_axis_field == "sales"
    assert len(spec.plotly_data) == 1
    assert spec.plotly_data[0]["type"] == "bar"
    assert spec.plotly_data[0]["x"] == ["Electronics", "Apparel", "Home & Kitchen", "Books"]


def test_visualization_pie_chart_for_status_breakdown():
    rows = [
        {"order_status": "delivered", "count": 17274},
        {"order_status": "cancelled", "count": 650},
        {"order_status": "returned", "count": 420},
    ]
    exec_result = QueryExecutionResult(
        sql="SELECT order_status, COUNT(*) as count FROM orders GROUP BY order_status",
        columns=["order_status", "count"],
        rows=rows,
        row_count=len(rows),
        execution_time_ms=4.0,
    )
    route = RouteResult(intent="descriptive", confidence=0.90, reasoning="Status breakdown")
    spec = visualization_agent.derive_chart_specification("Order count by status share", route, exec_result)

    assert spec.chart_type == ChartType.PIE
    assert spec.fallback_to_table is False
    assert len(spec.plotly_data) == 1
    assert spec.plotly_data[0]["type"] == "pie"
    assert spec.plotly_data[0]["labels"] == ["delivered", "cancelled", "returned"]


def test_visualization_table_fallback_for_single_row_scalar():
    rows = [{"total_revenue": 20891624.33}]
    exec_result = QueryExecutionResult(
        sql="SELECT SUM(total_amount) as total_revenue FROM orders",
        columns=["total_revenue"],
        rows=rows,
        row_count=1,
        execution_time_ms=3.0,
    )
    route = RouteResult(intent="descriptive", confidence=0.98, reasoning="Scalar metric")
    spec = visualization_agent.derive_chart_specification("What is total revenue?", route, exec_result)

    assert spec.chart_type == ChartType.TABLE
    assert spec.fallback_to_table is True


def test_visualization_table_fallback_for_non_numeric():
    rows = [
        {"customer_id": "1", "notes": "Active VIP buyer"},
        {"customer_id": "2", "notes": "New customer"},
    ]
    exec_result = QueryExecutionResult(
        sql="SELECT customer_id, notes FROM customer_notes",
        columns=["customer_id", "notes"],
        rows=rows,
        row_count=2,
        execution_time_ms=2.0,
    )
    route = RouteResult(intent="descriptive", confidence=0.85, reasoning="Text notes")
    spec = visualization_agent.derive_chart_specification("Show customer notes", route, exec_result)

    assert spec.chart_type == ChartType.TABLE
    assert spec.fallback_to_table is True
