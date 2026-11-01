"""
API endpoints for deterministic analysis tools.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from backend.app.analysis.contracts import AnalysisToolResult
from backend.app.analysis.registry import ToolMetadata, analysis_registry
from backend.app.core.models import APIResponse

router = APIRouter(prefix="/analysis", tags=["Analysis Tools"])


class AnomalyRequest(BaseModel):
    records: List[Dict[str, Any]]
    date_col: str
    metric_col: str
    threshold: float = 2.5
    metric_name: Optional[str] = None


class ForecastRequest(BaseModel):
    records: List[Dict[str, Any]]
    date_col: str
    value_col: str
    horizon_periods: int = 14
    frequency: str = "D"
    metric_name: Optional[str] = None


class ScenarioRequest(BaseModel):
    baseline_value: float
    parameter_name: str
    shock_pct: float
    elasticity: float = -1.0
    target_metric: str = "revenue"


class OptimizationRequest(BaseModel):
    total_budget: float
    channels: List[str]
    historical_roas: Dict[str, float]
    min_allocation_pct: float = 0.05
    max_allocation_pct: float = 0.50


@router.get(
    "/tools",
    response_model=APIResponse[List[ToolMetadata]],
    summary="List registered deterministic analysis tools",
)
async def list_analysis_tools(request: Request) -> APIResponse[List[ToolMetadata]]:
    request_id = getattr(request.state, "request_id", None)
    tools = analysis_registry.list_tools()
    return APIResponse(success=True, data=tools, request_id=request_id)


@router.post(
    "/churn",
    response_model=APIResponse[AnalysisToolResult],
    summary="Run customer churn risk and segment prioritization analysis",
)
async def run_churn_analysis(request: Request) -> APIResponse[AnalysisToolResult]:
    request_id = getattr(request.state, "request_id", None)
    result = analysis_registry.execute_tool("analyze_customer_churn_risk")
    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.post(
    "/anomalies",
    response_model=APIResponse[AnalysisToolResult],
    summary="Run robust anomaly detection with data quality screen",
)
async def run_anomaly_detection(
    body: AnomalyRequest,
    request: Request,
) -> APIResponse[AnalysisToolResult]:
    request_id = getattr(request.state, "request_id", None)
    result = analysis_registry.execute_tool(
        "detect_anomalies",
        records=body.records,
        date_col=body.date_col,
        metric_col=body.metric_col,
        threshold=body.threshold,
        metric_name=body.metric_name,
    )
    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.post(
    "/forecast",
    response_model=APIResponse[AnalysisToolResult],
    summary="Run deterministic time-series forecasting with intervals",
)
async def run_forecast(
    body: ForecastRequest,
    request: Request,
) -> APIResponse[AnalysisToolResult]:
    request_id = getattr(request.state, "request_id", None)
    result = analysis_registry.execute_tool(
        "forecast_series",
        records=body.records,
        date_col=body.date_col,
        value_col=body.value_col,
        horizon_periods=body.horizon_periods,
        frequency=body.frequency,
        metric_name=body.metric_name,
    )
    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.post(
    "/scenario",
    response_model=APIResponse[AnalysisToolResult],
    summary="Run what-if scenario elasticity simulation",
)
async def run_scenario(
    body: ScenarioRequest,
    request: Request,
) -> APIResponse[AnalysisToolResult]:
    request_id = getattr(request.state, "request_id", None)
    result = analysis_registry.execute_tool(
        "simulate_scenario",
        baseline_value=body.baseline_value,
        parameter_name=body.parameter_name,
        shock_pct=body.shock_pct,
        elasticity=body.elasticity,
        target_metric=body.target_metric,
    )
    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.post(
    "/optimize",
    response_model=APIResponse[AnalysisToolResult],
    summary="Run prescriptive budget allocation optimization",
)
async def run_optimization(
    body: OptimizationRequest,
    request: Request,
) -> APIResponse[AnalysisToolResult]:
    request_id = getattr(request.state, "request_id", None)
    result = analysis_registry.execute_tool(
        "optimize_budget_allocation",
        total_budget=body.total_budget,
        channels=body.channels,
        historical_roas=body.historical_roas,
        min_allocation_pct=body.min_allocation_pct,
        max_allocation_pct=body.max_allocation_pct,
    )
    return APIResponse(success=result.success, data=result, request_id=request_id)

