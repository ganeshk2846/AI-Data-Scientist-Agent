"""
Typed models for question execution workflow, progress states, and results.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field
from backend.app.agents.router import RouteResult
from backend.app.sql.executor import QueryExecutionResult

WorkflowProgressState = Literal[
    "understanding_question",
    "retrieving_schema",
    "generating_query",
    "validating_query",
    "running_query",
    "verifying_results",
    "composing_answer",
    "completed",
    "failed",
]


class StepTrace(BaseModel):
    step: WorkflowProgressState
    status: Literal["running", "succeeded", "failed", "skipped"]
    duration_ms: float = 0.0
    message: str
    metadata: Optional[Dict[str, Any]] = None


class VerificationResult(BaseModel):
    is_valid: bool
    empty_result: bool = False
    row_count: int = 0
    checks_passed: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class QueryWorkflowResult(BaseModel):
    """Complete vertical slice execution result."""
    run_id: str
    query: str
    route: RouteResult
    selected_tables: List[str]
    generated_sql: Optional[str] = None
    sanitized_sql: Optional[str] = None
    query_result: Optional[QueryExecutionResult] = None
    verification: Optional[VerificationResult] = None
    composed_answer: str
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    trace_steps: List[StepTrace] = Field(default_factory=list)
    total_duration_ms: float = 0.0
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
