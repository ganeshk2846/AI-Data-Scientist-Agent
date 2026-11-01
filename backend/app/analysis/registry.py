"""
Central Analysis Tool Registry for the Data Scientist Agent.
Registers pure deterministic analysis tools and exposes discovery metadata.
"""

from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel
from backend.app.analysis.anomalies import detect_anomalies
from backend.app.analysis.churn import analyze_customer_churn_risk
from backend.app.analysis.contracts import AnalysisToolResult, AnalysisType
from backend.app.analysis.descriptive import compare_periods
from backend.app.analysis.diagnostic import analyze_drivers
from backend.app.analysis.forecasting import forecast_series
from backend.app.analysis.optimization import optimize_budget_allocation
from backend.app.analysis.scenarios import simulate_scenario


class ToolMetadata(BaseModel):
    tool_name: str
    analysis_type: AnalysisType
    description: str
    required_inputs: List[str]
    optional_inputs: List[str] = []
    when_to_abstain: str


class AnalysisToolRegistry:
    """Registry maintaining all typed analysis tools."""

    def __init__(self):
        self._tools: Dict[str, Callable[..., AnalysisToolResult]] = {
            "compare_periods": compare_periods,
            "detect_anomalies": detect_anomalies,
            "analyze_drivers": analyze_drivers,
            "forecast_series": forecast_series,
            "simulate_scenario": simulate_scenario,
            "analyze_customer_churn_risk": analyze_customer_churn_risk,
            "optimize_budget_allocation": optimize_budget_allocation,
        }

        self._metadata: Dict[str, ToolMetadata] = {
            "compare_periods": ToolMetadata(
                tool_name="compare_periods",
                analysis_type=AnalysisType.PERIOD_COMPARISON,
                description="Computes exact period-over-period delta and mix contribution along a dimension.",
                required_inputs=["records", "metric_col", "period_col", "period_a_val", "period_b_val"],
                optional_inputs=["dimension_col", "metric_name"],
                when_to_abstain="Input dataset is empty or required period values are not present in records.",
            ),
            "detect_anomalies": ToolMetadata(
                tool_name="detect_anomalies",
                analysis_type=AnalysisType.ANOMALY_DETECTION,
                description="Detects anomalous values using robust median/MAD z-scores and screens for duplicate batch load artifacts.",
                required_inputs=["records", "date_col", "metric_col"],
                optional_inputs=["threshold", "metric_name"],
                when_to_abstain="Fewer than 5 data points provided.",
            ),
            "analyze_drivers": ToolMetadata(
                tool_name="analyze_drivers",
                analysis_type=AnalysisType.DRIVER_ANALYSIS,
                description="Decomposes total metric variance across categorical dimensions with sample sizes and non-causal disclaimer.",
                required_inputs=["records", "metric_col", "dimension_col"],
                optional_inputs=["period_col", "period_a_val", "period_b_val", "metric_name"],
                when_to_abstain="Fewer than 2 records or missing dimension columns.",
            ),
            "forecast_series": ToolMetadata(
                tool_name="forecast_series",
                analysis_type=AnalysisType.FORECAST,
                description="Produces deterministic trend forecast with expanding 80%/95% confidence intervals and out-of-sample backtesting.",
                required_inputs=["records", "date_col", "value_col"],
                optional_inputs=["horizon_periods", "frequency", "metric_name"],
                when_to_abstain="Fewer than 10 chronological observations available.",
            ),
            "simulate_scenario": ToolMetadata(
                tool_name="simulate_scenario",
                analysis_type=AnalysisType.SCENARIO,
                description="Simulates parameter percentage shocks with explicit price/demand elasticity and sensitivity bounds.",
                required_inputs=["baseline_value", "parameter_name", "shock_pct"],
                optional_inputs=["elasticity", "target_metric"],
                when_to_abstain="Baseline value is less than or equal to zero.",
            ),
            "analyze_customer_churn_risk": ToolMetadata(
                tool_name="analyze_customer_churn_risk",
                analysis_type=AnalysisType.CHURN_RISK,
                description="Analyzes customer segments and computes expected revenue at risk with Wilson score confidence intervals.",
                required_inputs=[],
                optional_inputs=["db_path", "inactivity_days_threshold"],
                when_to_abstain="Customer segment records or order data unavailable.",
            ),
            "optimize_budget_allocation": ToolMetadata(
                tool_name="optimize_budget_allocation",
                analysis_type=AnalysisType.OPTIMIZATION,
                description="Prescriptive resource allocation using scipy.optimize to maximize revenue with diminishing returns under budget bounds.",
                required_inputs=["total_budget", "channels", "historical_roas"],
                optional_inputs=["min_allocation_pct", "max_allocation_pct"],
                when_to_abstain="Total budget <= 0 or fewer than 2 channels provided.",
            ),
        }

    def list_tools(self) -> List[ToolMetadata]:
        return list(self._metadata.values())

    def get_tool_metadata(self, name: str) -> Optional[ToolMetadata]:
        return self._metadata.get(name)

    def execute_tool(self, name: str, **kwargs: Any) -> AnalysisToolResult:
        if name not in self._tools:
            raise ValueError(f"Analysis tool '{name}' is not registered.")
        return self._tools[name](**kwargs)

    def detect_intent(self, query: str) -> Optional[str]:
        """Infers appropriate analysis tool name from query intent."""
        q = query.lower()
        if any(w in q for w in ["forecast", "predict", "projection", "next 14 days", "future sales"]):
            return "forecast_series"
        if any(w in q for w in ["anomaly", "anomalies", "spike", "outlier", "irregular", "unusual"]):
            return "detect_anomalies"
        if any(w in q for w in ["why did", "driver", "cause of", "contributing factors", "decompose variance"]):
            return "analyze_drivers"
        if any(w in q for w in ["churn", "at risk", "retention", "dormant customers", "customer segments"]):
            return "analyze_customer_churn_risk"
        if any(w in q for w in ["what if", "scenario", "price increase", "simulate"]):
            return "simulate_scenario"
        if any(w in q for w in ["optimize budget", "allocation", "allocate spend", "roas optimization"]):
            return "optimize_budget_allocation"
        if any(w in q for w in ["compare", "versus", "vs", "growth rate", "year over year", "yoy"]):
            return "compare_periods"
        return None


analysis_registry = AnalysisToolRegistry()
