"""
Pydantic contracts and data structures for deterministic analysis tools.
Pure functions, explicit units, provenance tracking, and typed errors.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AnalysisType(str, Enum):
    PERIOD_COMPARISON = "period_comparison"
    TREND_DECOMPOSITION = "trend_decomposition"
    ANOMALY_DETECTION = "anomaly_detection"
    DRIVER_ANALYSIS = "driver_analysis"
    FORECAST = "forecast"
    SCENARIO = "scenario"
    CHURN_RISK = "churn_risk"
    OPTIMIZATION = "optimization"


class ProvenanceInfo(BaseModel):
    source_dataset: str = "ecommerce.sqlite"
    time_window: str = "2023-01-01 to 2025-12-31"
    record_count: int = 0
    computed_at: str
    method_name: str
    assumptions: List[str] = Field(default_factory=list)


class PeriodComparisonResult(BaseModel):
    metric_name: str
    period_a_label: str
    period_a_value: float
    period_b_label: str
    period_b_value: float
    delta_absolute: float
    delta_percentage: float
    dimension_breakdown: List[Dict[str, Any]] = Field(default_factory=list)


class AnomalyPoint(BaseModel):
    date: str
    actual_value: float
    expected_value: float
    z_score: float
    is_anomaly: bool
    severity: str  # "mild", "severe", "none"
    quality_flag: Optional[str] = None  # e.g., "suspected_duplicate_batch", "gap_missing"


class AnomalyDetectionResult(BaseModel):
    metric_name: str
    threshold: float
    total_data_points: int
    anomaly_count: int
    anomalies: List[AnomalyPoint]
    method: str
    quality_warning: Optional[str] = None


class DriverContribution(BaseModel):
    dimension_value: str
    period_a_value: float
    period_b_value: float
    delta: float
    pct_of_total_delta: float
    direction: str  # "positive", "negative", "neutral"


class DriverAnalysisResult(BaseModel):
    metric_name: str
    dimension: str
    total_delta: float
    sample_size: int
    drivers: List[DriverContribution]
    causal_claim_disclaimer: str = (
        "Statistical decomposition reflects observational correlation and accounting identity, not causal proof."
    )


class ForecastPoint(BaseModel):
    date: str
    point_forecast: float
    lower_bound_80: float
    upper_bound_80: float
    lower_bound_95: float
    upper_bound_95: float


class ForecastResult(BaseModel):
    metric_name: str
    horizon_periods: int
    frequency: str
    points: List[ForecastPoint]
    model_used: str
    backtest_mae: Optional[float] = None
    backtest_rmse: Optional[float] = None
    backtest_mape_pct: Optional[float] = None
    is_sufficient_data: bool = True
    limitations: List[str] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    target_metric: str
    baseline_value: float
    simulated_value: float
    delta_absolute: float
    delta_percentage: float
    assumptions_applied: Dict[str, Any]
    sensitivities: List[Dict[str, Any]] = Field(default_factory=list)


class SegmentChurnRisk(BaseModel):
    segment_name: str
    customer_count: int
    active_count: int
    churned_count: int
    churn_rate_pct: float
    total_historical_spend: float
    revenue_at_risk: float
    confidence_interval_low: float
    confidence_interval_high: float
    actionability_rank: int


class ChurnAnalysisResult(BaseModel):
    cutoff_date: str
    inactivity_threshold_days: int
    total_customers_analyzed: int
    total_revenue_at_risk: float
    segments: List[SegmentChurnRisk]
    observations: List[str] = Field(default_factory=list)


class OptimizationResult(BaseModel):
    objective: str
    total_budget: float
    allocations: Dict[str, float]
    expected_total_revenue: float
    constraints_satisfied: bool
    status: str
    notes: List[str] = Field(default_factory=list)


class AnalysisToolResult(BaseModel):
    tool_name: str
    analysis_type: AnalysisType
    success: bool
    provenance: ProvenanceInfo
    abstain_reason: Optional[str] = None
    period_comparison: Optional[PeriodComparisonResult] = None
    anomaly_detection: Optional[AnomalyDetectionResult] = None
    driver_analysis: Optional[DriverAnalysisResult] = None
    forecast: Optional[ForecastResult] = None
    scenario: Optional[ScenarioResult] = None
    churn_risk: Optional[ChurnAnalysisResult] = None
    optimization: Optional[OptimizationResult] = None
