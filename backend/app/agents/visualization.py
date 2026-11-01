"""
Visualization Agent.
Selects appropriate chart encodings based on query intent and result data shape.
Constructs validated Plotly data traces and layout configurations,
with strict fallback to tabular representation when data is unsuitable.
"""

from typing import Any, Dict, List, Optional
from backend.app.agents.contracts import ChartSpecification, ChartType
from backend.app.agents.router import RouteResult
from backend.app.sql.executor import QueryExecutionResult


DARK_LAYOUT_TEMPLATE = {
    "paper_bgcolor": "rgba(0,0,0,0)",
    "plot_bgcolor": "rgba(0,0,0,0)",
    "font": {"family": "Inter, system-ui, sans-serif", "color": "#94a3b8", "size": 12},
    "margin": {"l": 50, "r": 20, "t": 40, "b": 45},
    "hovermode": "closest",
    "autosize": True,
    "xaxis": {
        "gridcolor": "#1e293b",
        "zerolinecolor": "#334155",
        "tickfont": {"color": "#94a3b8"},
        "showline": True,
        "linecolor": "#334155",
    },
    "yaxis": {
        "gridcolor": "#1e293b",
        "zerolinecolor": "#334155",
        "tickfont": {"color": "#94a3b8"},
        "showline": True,
        "linecolor": "#334155",
    },
}


class VisualizationAgent:
    """Creates typed visualization specifications with complete Plotly payloads."""

    def derive_chart_specification(
        self,
        query: str,
        route: RouteResult,
        result: QueryExecutionResult,
    ) -> ChartSpecification:
        # Fallback to table if rows are empty or fewer than 2 columns
        if result.row_count == 0 or len(result.columns) < 2:
            return ChartSpecification(
                chart_type=ChartType.TABLE,
                title="Tabular Data View",
                data_points_count=result.row_count,
                fallback_to_table=True,
                description="Result shape is best presented as an exact tabular view.",
                alt_text="Table presenting returned data rows.",
            )

        cols_lower = [c.lower() for c in result.columns]

        # 1. Detect candidate x-axis (date or categorical column)
        date_col = None
        for i, col in enumerate(cols_lower):
            if any(k in col for k in ["date", "time", "month", "year", "day"]):
                date_col = result.columns[i]
                break

        # 2. Detect candidate y-axis (numeric metric column)
        metric_col = None
        for i, col in enumerate(cols_lower):
            if any(k in col for k in ["total", "amount", "revenue", "count", "cnt", "sum", "avg", "spend", "sales", "price", "val", "margin"]):
                metric_col = result.columns[i]
                break

        if not metric_col and len(result.columns) >= 2:
            metric_col = result.columns[1]

        x_field = date_col or result.columns[0]
        y_field = metric_col

        # Validate that y_field can be parsed as numbers
        y_vals: List[float] = []
        x_vals: List[str] = []
        is_numeric_valid = True

        for r in result.rows:
            raw_y = r.get(y_field)
            raw_x = r.get(x_field)
            try:
                if raw_y is not None:
                    y_vals.append(float(raw_y))
                else:
                    y_vals.append(0.0)
                x_vals.append(str(raw_x) if raw_x is not None else "")
            except (ValueError, TypeError):
                is_numeric_valid = False
                break

        if not is_numeric_valid or not y_vals:
            return ChartSpecification(
                chart_type=ChartType.TABLE,
                title="Tabular Data View",
                data_points_count=result.row_count,
                fallback_to_table=True,
                description="Column values are non-numeric; displaying standard data table.",
                alt_text="Table view of query results.",
            )

        metric_label = y_field.replace("_", " ").title()
        x_label = x_field.replace("_", " ").title()

        # 3. Determine Chart Type
        # Case A: Line chart for time-series trend
        if date_col is not None or route.intent == "trend":
            plotly_data = [
                {
                    "type": "scatter",
                    "mode": "lines+markers",
                    "x": x_vals,
                    "y": y_vals,
                    "name": metric_label,
                    "line": {"color": "#6366f1", "width": 3},
                    "marker": {"size": 6, "color": "#818cf8"},
                    "hovertemplate": f"<b>{x_label}:</b> %{{x}}<br><b>{metric_label}:</b> %{{y:,.2f}}<extra></extra>",
                }
            ]
            layout = {
                **DARK_LAYOUT_TEMPLATE,
                "title": {"text": f"{metric_label} Over Time", "font": {"color": "#f8fafc", "size": 14}},
                "xaxis": {**DARK_LAYOUT_TEMPLATE["xaxis"], "title": {"text": x_label}},
                "yaxis": {**DARK_LAYOUT_TEMPLATE["yaxis"], "title": {"text": metric_label}},
            }
            return ChartSpecification(
                chart_type=ChartType.LINE,
                title=f"{metric_label} Over Time",
                subtitle=f"Time-series trend indexed by {x_label}",
                x_axis_field=x_field,
                y_axis_field=y_field,
                data_points_count=len(y_vals),
                fallback_to_table=False,
                description=f"Interactive line chart showing {metric_label} across {x_label}.",
                alt_text=f"Line graph displaying {metric_label} from {x_vals[0] if x_vals else ''} to {x_vals[-1] if x_vals else ''}.",
                plotly_data=plotly_data,
                plotly_layout=layout,
            )

        # Case B: Pie / Donut Chart for small categorical shares (between 2 and 6 categories)
        if 2 <= len(x_vals) <= 6 and ("status" in x_field.lower() or "channel" in x_field.lower() or "share" in query.lower()):
            plotly_data = [
                {
                    "type": "pie",
                    "labels": x_vals,
                    "values": y_vals,
                    "hole": 0.4,
                    "textinfo": "label+percent",
                    "marker": {
                        "colors": ["#6366f1", "#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6"]
                    },
                    "hovertemplate": f"<b>%{{label}}:</b> %{{value:,.2f}} (%{{percent}})<extra></extra>",
                }
            ]
            layout = {
                **DARK_LAYOUT_TEMPLATE,
                "title": {"text": f"{metric_label} Share by {x_label}", "font": {"color": "#f8fafc", "size": 14}},
            }
            return ChartSpecification(
                chart_type=ChartType.PIE,
                title=f"{metric_label} Breakdown",
                subtitle=f"Proportion across {x_label}",
                category_field=x_field,
                y_axis_field=y_field,
                data_points_count=len(y_vals),
                fallback_to_table=False,
                description=f"Donut chart breaking down {metric_label} by {x_label}.",
                alt_text=f"Donut chart displaying {metric_label} distribution across {x_label}.",
                plotly_data=plotly_data,
                plotly_layout=layout,
            )

        # Case C: Bar Chart for category comparisons
        plotly_data = [
            {
                "type": "bar",
                "x": x_vals,
                "y": y_vals,
                "name": metric_label,
                "marker": {
                    "color": "#3b82f6",
                    "line": {"color": "#60a5fa", "width": 1},
                },
                "hovertemplate": f"<b>{x_label}:</b> %{{x}}<br><b>{metric_label}:</b> %{{y:,.2f}}<extra></extra>",
            }
        ]
        layout = {
            **DARK_LAYOUT_TEMPLATE,
            "title": {"text": f"{metric_label} by {x_label}", "font": {"color": "#f8fafc", "size": 14}},
            "xaxis": {**DARK_LAYOUT_TEMPLATE["xaxis"], "title": {"text": x_label}},
            "yaxis": {**DARK_LAYOUT_TEMPLATE["yaxis"], "title": {"text": metric_label}},
        }
        return ChartSpecification(
            chart_type=ChartType.BAR,
            title=f"{metric_label} by {x_label}",
            subtitle=f"Categorical ranking across {x_label}",
            x_axis_field=x_field,
            y_axis_field=y_field,
            data_points_count=len(y_vals),
            fallback_to_table=False,
            description=f"Interactive bar chart comparing {metric_label} grouped across {x_label}.",
            alt_text=f"Bar chart comparing {metric_label} across {len(x_vals)} {x_label} categories.",
            plotly_data=plotly_data,
            plotly_layout=layout,
        )


visualization_agent = VisualizationAgent()
