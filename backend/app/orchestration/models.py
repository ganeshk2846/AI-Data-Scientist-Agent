"""
backend/app/orchestration/models.py
Phase 5: Agentic Orchestration Contracts and Data Models.

Defines schemas for:
1. Specialist roles and execution task statuses.
2. Structured agent task specifications (DAG nodes).
3. Executive management response divided into WHAT, WHY, WHAT NEXT, SO WHAT.
4. Supervisor execution result with full task provenance, execution metrics, and database isolation.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field, ConfigDict

from backend.app.analysis.contracts_v2 import StandardizedAnalyticalResult, IntentCategory


class SpecialistRole(str, Enum):
    """Specialized analytical agent interfaces orchestrated by the Supervisor."""
    DATA_RETRIEVAL = "DATA_RETRIEVAL"
    DIAGNOSTIC = "DIAGNOSTIC"
    PREDICTIVE = "PREDICTIVE"
    PRESCRIPTIVE = "PRESCRIPTIVE"
    CRITIC = "CRITIC"


class TaskStatus(str, Enum):
    """Lifecycle states of an orchestrated specialist task."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ABSTAINED = "ABSTAINED"


class AgentTask(BaseModel):
    """Structured task record tracking an analytical stage within the orchestration plan."""
    model_config = ConfigDict(extra="ignore")

    task_id: str
    specialist: SpecialistRole
    task_type: str
    input_references: List[str] = Field(default_factory=list)
    expected_output_type: str = "result"
    status: TaskStatus = TaskStatus.PENDING
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    duration_ms: float = 0.0
    error_or_abstain_reason: Optional[str] = None
    evidence_references: List[str] = Field(default_factory=list)
    output_summary: Optional[str] = None


class ExecutiveSection(BaseModel):
    """Individual executive response section for business decision-makers."""
    model_config = ConfigDict(extra="ignore")

    title: str = Field(..., description="Section title: WHAT, WHY, WHAT NEXT, or SO WHAT")
    headline: str = Field(..., description="Single-sentence punchy executive summary of findings")
    content: str = Field(..., description="Detailed narrative explaining metrics and insights")
    kpis: Dict[str, Any] = Field(default_factory=dict, description="Key numerical metrics and values")
    evidence_references: List[str] = Field(default_factory=list, description="Columns, tables, queries, or records supporting claims")
    disclaimers: List[str] = Field(default_factory=list, description="Methodological limitations, non-causal warnings, or advisory notices")


class ManagementResponse(BaseModel):
    """
    Structured executive response synthesizing analytical results into actionable management intelligence.
    Only populated sections relevant to the inquiry are included (no fabricated or empty sections).
    """
    model_config = ConfigDict(extra="ignore")

    what: Optional[ExecutiveSection] = None       # Descriptive: What happened? (KPIs, trends, historical changes)
    why: Optional[ExecutiveSection] = None        # Diagnostic: Why did it happen? (Drivers, anomalies, non-causal correlation)
    what_next: Optional[ExecutiveSection] = None  # Predictive: What might happen? (Forecasts, intervals, horizon)
    so_what: Optional[ExecutiveSection] = None    # Prescriptive: What should management consider doing? (Optimization, advisory)
    executive_summary: str = ""
    composed_markdown: str = ""


class SupervisorExecutionResult(BaseModel):
    """Complete output of the central Agentic Supervisor orchestrating the multi-agent decision support engine."""
    model_config = ConfigDict(extra="ignore")

    execution_id: str
    question: str
    session_id: str = "default_session"
    database_fingerprint: str = "default_fp"
    primary_intent: IntentCategory = IntentCategory.DESCRIPTIVE
    plan_summary: str = ""
    tasks: List[AgentTask] = Field(default_factory=list)
    management_response: ManagementResponse = Field(default_factory=ManagementResponse)
    analytical_result: Optional[StandardizedAnalyticalResult] = None
    metrics: Dict[str, Any] = Field(default_factory=dict)
    success: bool = True
    abstain_reason: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
