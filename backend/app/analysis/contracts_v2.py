"""
backend/app/analysis/contracts_v2.py
Domain-Independent Analytical Intelligence Contracts for Phase 4.
Establishes standardized interfaces for:
1. Intent & Complexity Classification
2. Analytical Planning
3. Standardized Analytical Execution Results
4. Result Faithfulness & Numerical Fact Verification
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict


class IntentCategory(str, Enum):
    """Four core analytical intents plus standard SQL lookup."""
    DESCRIPTIVE = "DESCRIPTIVE"     # What happened?
    DIAGNOSTIC = "DIAGNOSTIC"       # Why did it happen?
    PREDICTIVE = "PREDICTIVE"       # What could happen next?
    PRESCRIPTIVE = "PRESCRIPTIVE"   # What should we do?
    SQL_LOOKUP = "SQL_LOOKUP"       # Standard data retrieval without advanced analysis


class ComplexityLevel(str, Enum):
    """Analytical complexity grading."""
    SIMPLE = "SIMPLE"               # Single aggregation or table lookup
    MODERATE = "MODERATE"           # Period-over-period, multi-table grouping, basic filtering
    COMPLEX = "COMPLEX"             # Anomaly detection, driver decomposition, correlation
    ADVANCED = "ADVANCED"           # Time-series ML forecasting, constrained optimization


class AnalyticalMethod(str, Enum):
    """Granular analytical method types."""
    # Descriptive methods
    METRIC_AGGREGATION = "metric_aggregation"
    PERIOD_OVER_PERIOD = "period_over_period"
    TREND_ANALYSIS = "trend_analysis"
    SEGMENTATION = "segmentation"
    DESCRIPTIVE_STATS = "descriptive_stats"

    # Diagnostic methods
    VARIANCE_DECOMPOSITION = "variance_decomposition"
    ANOMALY_DETECTION = "anomaly_detection"
    STATISTICAL_CORRELATION = "statistical_correlation"
    HYPOTHESIS_TESTING = "hypothesis_testing"

    # Predictive methods
    TIME_SERIES_FORECAST = "time_series_forecast"
    SUPERVISED_REGRESSION = "supervised_regression"
    SUPERVISED_CLASSIFICATION = "supervised_classification"

    # Prescriptive methods
    WHAT_IF_SCENARIO = "what_if_scenario"
    CONSTRAINED_OPTIMIZATION = "constrained_optimization"

    # Fallback
    SQL_QUERY_ONLY = "sql_query_only"


class IntentClassificationResult(BaseModel):
    """Result of Intent & Complexity Classifier."""
    model_config = ConfigDict(frozen=True)

    primary_intent: IntentCategory
    complexity: ComplexityLevel
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    all_probabilities: Dict[str, float] = Field(default_factory=dict)
    is_ambiguous: bool = False
    requires_clarification: bool = False
    suggested_clarification: Optional[str] = None
    recommended_methods: List[AnalyticalMethod] = Field(default_factory=list)
    # Composite multi-intent support
    is_composite: bool = False
    composite_intents: List[IntentCategory] = Field(default_factory=list)
    execution_sequence: List[str] = Field(default_factory=list)


class ClaimType(str, Enum):
    """Categories of factual, statistical, and narrative claims."""
    NUMERICAL = "NUMERICAL"
    DIRECTIONAL = "DIRECTIONAL"
    COMPARATIVE = "COMPARATIVE"
    STATISTICAL = "STATISTICAL"
    DRIVER_CONTRIBUTION = "DRIVER_CONTRIBUTION"
    CAUSAL = "CAUSAL"
    PREDICTIVE = "PREDICTIVE"
    RECOMMENDATION = "RECOMMENDATION"


class StructuredClaim(BaseModel):
    """Individual claim extracted from analysis narrative linked to empirical evidence."""
    model_config = ConfigDict(frozen=True)

    claim_id: str
    claim_type: ClaimType
    statement: str
    verified: bool = False
    evidence_reference: Optional[str] = None
    discrepancy: Optional[str] = None


class AnalyticalPlan(BaseModel):
    """Structured plan specifying the analytical workflow prior to execution."""
    model_config = ConfigDict(frozen=True)

    plan_id: str
    question: str
    intent: IntentCategory
    complexity: ComplexityLevel
    analytical_objective: str
    relevant_tables: List[str] = Field(default_factory=list)
    required_columns: Dict[str, List[str]] = Field(default_factory=dict)
    relevant_metrics: List[str] = Field(default_factory=list)
    filters: List[Dict[str, Any]] = Field(default_factory=list)
    time_dimension: Optional[str] = None
    target_variable: Optional[str] = None
    candidate_methods: List[AnalyticalMethod] = Field(default_factory=list)
    selected_method: AnalyticalMethod
    data_extraction_sql: Optional[str] = None
    validation_requirements: List[str] = Field(default_factory=list)
    expected_output_format: str = "table_and_chart"
    is_executable: bool = True
    abstain_reason: Optional[str] = None


class FaithfulnessReport(BaseModel):
    """Validation report ensuring narrative faithfulness against numerical facts and evidence."""
    is_faithful: bool = True
    total_claims_checked: int = 0
    verified_claims: int = 0
    discrepancies: List[str] = Field(default_factory=list)
    confidence_discount: float = 0.0
    structured_claims: List[StructuredClaim] = Field(default_factory=list)


class StandardizedAnalyticalResult(BaseModel):
    """Reusable result contract for all Phase 4 analytical outputs."""
    analysis_id: str
    analytical_type: IntentCategory
    analysis_question: str
    success: bool
    selected_methods: List[str] = Field(default_factory=list)
    source_tables: List[str] = Field(default_factory=list)
    source_columns: List[str] = Field(default_factory=list)
    executed_queries: List[str] = Field(default_factory=list)
    result_data: List[Dict[str, Any]] = Field(default_factory=list)
    computed_metrics: Dict[str, Any] = Field(default_factory=dict)
    model_information: Dict[str, Any] = Field(default_factory=dict)
    validation_results: Dict[str, Any] = Field(default_factory=dict)
    faithfulness: Optional[FaithfulnessReport] = None
    faithfulness_report: Optional[FaithfulnessReport] = None
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)
    uncertainty_notes: List[str] = Field(default_factory=list)
    findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    recommended_next_steps: List[str] = Field(default_factory=list)
    visualization_config: Optional[Dict[str, Any]] = None
    abstain_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

