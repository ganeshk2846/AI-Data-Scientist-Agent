"""
Visualization Agent.
Selects appropriate chart encodings based on query intent and result data shape.
Always provides a table fallback when data is unsuitable for charting.
"""

from typing import Any, Dict, List, Optional
from backend.app.agents.contracts import ChartSpecification, ChartType
from backend.app.agents.router import RouteResult
from backend.app.sql.executor import QueryExecutionResult


class VisualizationAgent:
    """Creates typed visualization specifications from executed query results."""

    def derive_chart_specification(
        self,
        query: str,
        route: RouteResult,
        result: QueryExecutionResult,
    ) -> ChartSpecification:
        # Fallback to table if rows are empty or only 1 column
        if result.row_count == 0 or len(result.columns) < 2:
            return ChartSpecification(
                chart_type=ChartType.TABLE,
                title="Query Results Table",
                data_points_count=result.row_count,
                fallback_to_table=True,
                description="Result shape is best presented as an exact tabular view.",
            )

        cols_lower = [c.lower() for c in result.columns]

        # Detect candidate x-axis (date or categorical column)
        date_col = None
        for i, col in enumerate(cols_lower):
            if any(k in col for k in ["date", "time", "month", "year", "day"]):
                date_col = result.columns[i]
                break

        # Detect candidate y-axis (numeric metric column)
        metric_col = None
        for i, col in enumerate(cols_lower):
            if any(k in col for k in ["total", "amount", "revenue", "count", "cnt", "sum", "avg", "spend", "sales", "subtotal", "val"]):
                metric_col = result.columns[i]
                break

        # If no explicit metric found, pick second column
        if not metric_col and len(result.columns) >= 2:
            metric_col = result.columns[1]

        # 1. Line Chart for trends over time
        if route.intent == "trend" or (date_col and metric_col):
            x_field = date_col or result.columns[0]
            return ChartSpecification(
                chart_type=ChartType.LINE,
                title=f"{metric_col.replace('_', ' ').title()} Over Time",
                x_axis_field=x_field,
                y_axis_field=metric_col,
                data_points_count=result.row_count,
                fallback_to_table=False,
                description=f"Time-series trend showing {metric_col} indexed by {x_field}.",
            )

        # 2. Bar Chart for category / segment / status comparisons
        category_col = result.columns[0]
        if metric_col and category_col != metric_col:
            return ChartSpecification(
                chart_type=ChartType.BAR,
                title=f"{metric_col.replace('_', ' ').title()} by {category_col.replace('_', ' ').title()}",
                x_axis_field=category_col,
                y_axis_field=metric_col,
                data_points_count=result.row_count,
                fallback_to_table=False,
                description=f"Categorical comparison of {metric_col} grouped across {category_col}.",
            )

        # Default fallback to Table
        return ChartSpecification(
            chart_type=ChartType.TABLE,
            title="Tabular Data View",
            data_points_count=result.row_count,
            fallback_to_table=True,
            description="Multi-dimensional records presented in standard tabular format.",
        )


visualization_agent = VisualizationAgent()
