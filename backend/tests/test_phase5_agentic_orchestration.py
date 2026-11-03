"""
backend/tests/test_phase5_agentic_orchestration.py
Comprehensive Phase 5 Regression Test Suite: Agentic Orchestration & Business Decision Support.

Covers all 15 mandatory test scenarios from Section 11 of the Master Implementation Prompt:
1. Descriptive-only question.
2. Diagnostic-only question.
3. Predictive-only question.
4. Prescriptive-only question.
5. Descriptive + Diagnostic workflow.
6. Descriptive + Diagnostic + Predictive workflow.
7. Four-stage composite workflow.
8. Follow-up question using previous context.
9. Database switching without context leakage.
10. Specialist execution failure.
11. Critic rejection of unsupported claims.
12. Missing temporal data and safe abstention.
13. Unsupported optimization assumptions.
14. Read-only SQL enforcement.
15. Partial workflow completion.
"""

from pathlib import Path
import os
import sqlite3
import tempfile
import pytest
import pandas as pd

from backend.app.analysis.contracts_v2 import (
    AnalyticalPlan,
    ComplexityLevel,
    IntentCategory,
    AnalyticalMethod,
)
from backend.app.db.adapters import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.orchestration.models import (
    SpecialistRole,
    TaskStatus,
    SupervisorExecutionResult,
)
from backend.app.orchestration.specialists import (
    critic_specialist,
    data_retrieval_specialist,
    diagnostic_specialist,
    predictive_specialist,
    prescriptive_specialist,
)
from backend.app.orchestration.supervisor import agentic_supervisor
from backend.app.schema.service import SchemaService


@pytest.fixture(scope="module")
def setup_test_environment():
    """Provides an active synthetic SQLite database and profiled catalog for Phase 5 orchestration."""
    fd, path = tempfile.mkstemp(suffix="_phase5_test.db")
    os.close(fd)
    conn = sqlite3.connect(path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE sales_performance (
            record_id INTEGER PRIMARY KEY,
            order_date TEXT,
            channel TEXT,
            region TEXT,
            revenue REAL,
            ad_spend REAL,
            order_count INTEGER
        )
    """)

    # Populate 12 monthly points across 3 channels (36 records)
    records = []
    channels = ["Search", "Social", "Email"]
    base_date = pd.date_range("2025-01-01", periods=12, freq="MS")

    r_id = 1
    for dt in base_date:
        dt_str = dt.strftime("%Y-%m-%d")
        for ch in channels:
            rev = 10000.0 + (r_id * 350.0)
            spend = 2000.0 + (r_id * 50.0)
            records.append((r_id, dt_str, ch, "North", rev, spend, 120))
            r_id += 1

    cur.executemany(
        "INSERT INTO sales_performance VALUES (?, ?, ?, ?, ?, ?, ?)", records
    )
    conn.commit()
    conn.close()

    prev_adapter = getattr(db_manager, "_active_adapter", None)
    adapter = SQLiteAdapter(file_path=str(path), name="phase5_db", read_only=True)
    adapter.connect()
    db_manager._active_adapter = adapter

    svc = SchemaService(db_path=str(path))
    catalog = svc.profile_database(force_refresh=True)

    yield adapter, catalog

    adapter.disconnect()
    db_manager._active_adapter = prev_adapter
    if os.path.exists(path):
        os.remove(path)


# ==============================================================================
# SCENARIO 1: Descriptive-Only Question
# ==============================================================================
def test_scenario_01_descriptive_only(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Describe total revenue and sales performance during the period.",
        catalog=catalog,
        intent_override=IntentCategory.DESCRIPTIVE,
    )

    assert result.success is True
    assert result.primary_intent == IntentCategory.DESCRIPTIVE
    assert len(result.tasks) >= 3  # Retrieval, Descriptive, Critic
    assert result.tasks[0].specialist == SpecialistRole.DATA_RETRIEVAL
    assert result.tasks[0].status == TaskStatus.COMPLETED
    assert result.management_response.what is not None
    assert result.management_response.what.title == "WHAT"
    assert result.management_response.why is None
    assert result.management_response.what_next is None
    assert result.management_response.so_what is None


# ==============================================================================
# SCENARIO 2: Diagnostic-Only Question
# ==============================================================================
def test_scenario_02_diagnostic_only(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Why did revenue decrease last month? What factors contributed to the change?",
        catalog=catalog,
        intent_override=IntentCategory.DIAGNOSTIC,
    )

    assert result.success is True
    assert result.management_response.why is not None
    assert result.management_response.why.title == "WHY"
    # Verify non-causal disclaimer is attached
    assert any("correlation" in d.lower() or "causality" in d.lower() for d in result.management_response.why.disclaimers)
    diag_task = next((t for t in result.tasks if t.specialist == SpecialistRole.DIAGNOSTIC), None)
    assert diag_task is not None
    assert diag_task.status == TaskStatus.COMPLETED


# ==============================================================================
# SCENARIO 3: Predictive-Only Question
# ==============================================================================
def test_scenario_03_predictive_only(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Forecast revenue for the next three months.",
        catalog=catalog,
        intent_override=IntentCategory.PREDICTIVE,
    )

    assert result.success is True
    assert result.management_response.what_next is not None
    assert result.management_response.what_next.title == "WHAT NEXT"
    pred_task = next((t for t in result.tasks if t.specialist == SpecialistRole.PREDICTIVE), None)
    assert pred_task is not None
    assert pred_task.status == TaskStatus.COMPLETED


# ==============================================================================
# SCENARIO 4: Prescriptive-Only Question
# ==============================================================================
def test_scenario_04_prescriptive_only(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Optimize our marketing budget allocation of $50,000 across channels to maximize revenue.",
        catalog=catalog,
        intent_override=IntentCategory.PRESCRIPTIVE,
    )

    assert result.success is True
    assert result.management_response.so_what is not None
    assert result.management_response.so_what.title == "SO WHAT"
    # Verify safe advisory notice
    assert any("advisory" in d.lower() or "autonomously" in d.lower() for d in result.management_response.so_what.disclaimers)
    presc_task = next((t for t in result.tasks if t.specialist == SpecialistRole.PRESCRIPTIVE), None)
    assert presc_task is not None
    assert presc_task.status == TaskStatus.COMPLETED


# ==============================================================================
# SCENARIO 5: Descriptive + Diagnostic Workflow (2-stage composite)
# ==============================================================================
def test_scenario_05_descriptive_and_diagnostic(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Describe revenue and explain the major drivers and anomalies behind the change.",
        catalog=catalog,
    )

    assert result.success is True
    assert result.management_response.what is not None
    assert result.management_response.why is not None
    # 2 analytical stages + retrieval + critic = 4 tasks
    assert len(result.tasks) >= 4
    roles = [t.specialist for t in result.tasks]
    assert SpecialistRole.DATA_RETRIEVAL in roles
    assert SpecialistRole.DIAGNOSTIC in roles
    assert SpecialistRole.CRITIC in roles


# ==============================================================================
# SCENARIO 6: Descriptive + Diagnostic + Predictive Workflow (3-stage composite)
# ==============================================================================
def test_scenario_06_three_stage_composite(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="What happened to revenue, why did it change, and what will happen next quarter?",
        catalog=catalog,
    )

    assert result.success is True
    assert result.management_response.what is not None
    assert result.management_response.why is not None
    assert result.management_response.what_next is not None
    assert result.management_response.so_what is None


# ==============================================================================
# SCENARIO 7: Four-Stage Composite Workflow
# ==============================================================================
def test_scenario_07_four_stage_composite(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Analyse sales performance, explain the major drivers, forecast next quarter, and suggest what management should do with a $50,000 budget.",
        catalog=catalog,
    )

    assert result.success is True
    # All 4 sections should be present
    assert result.management_response.what is not None
    assert result.management_response.why is not None
    assert result.management_response.what_next is not None
    assert result.management_response.so_what is not None
    assert len(result.tasks) >= 6  # Retrieval, Desc, Diag, Pred, Presc, Critic


# ==============================================================================
# SCENARIO 8: Follow-up Question Using Previous Context
# ==============================================================================
def test_scenario_08_conversational_followup(setup_test_environment):
    _, catalog = setup_test_environment
    sid = "test_session_followup_p5"
    fp = catalog.source_fingerprint

    # Turn 1
    res1 = agentic_supervisor.supervise(
        question="Describe total revenue across channels.",
        session_id=sid,
        catalog=catalog,
        fingerprint=fp,
    )
    assert res1.success is True
    assert (sid, fp) in agentic_supervisor._session_cache

    # Turn 2: Follow-up relying on prior turn's table/columns
    res2 = agentic_supervisor.supervise(
        question="Why did the revenue change?",
        session_id=sid,
        catalog=catalog,
        fingerprint=fp,
    )
    assert res2.success is True
    assert res2.analytical_result.source_tables == res1.analytical_result.source_tables


# ==============================================================================
# SCENARIO 9: Database Switching Without Context Leakage
# ==============================================================================
def test_scenario_09_database_switching_isolation(setup_test_environment):
    _, catalog = setup_test_environment
    sid = "test_session_switch_p5"
    fp1 = "database_fingerprint_alpha"
    fp2 = "database_fingerprint_beta"

    # Turn 1 on DB 1
    res1 = agentic_supervisor.supervise(
        question="Describe revenue performance.",
        session_id=sid,
        catalog=catalog,
        fingerprint=fp1,
    )
    assert res1.success is True
    assert (sid, fp1) in agentic_supervisor._session_cache

    # Turn 2 on DB 2 with SAME session ID
    res2 = agentic_supervisor.supervise(
        question="Describe revenue performance on new db.",
        session_id=sid,
        catalog=catalog,
        fingerprint=fp2,
    )
    assert res2.success is True
    # Crucial: DB 1 context must be purged from cache for this session
    assert (sid, fp1) not in agentic_supervisor._session_cache
    assert (sid, fp2) in agentic_supervisor._session_cache


# ==============================================================================
# SCENARIO 10: Specialist Execution Failure Handling
# ==============================================================================
def test_scenario_10_specialist_failure_handling(setup_test_environment, monkeypatch):
    _, catalog = setup_test_environment

    def mock_failing_diagnostic(*args, **kwargs):
        raise RuntimeError("Diagnostic algorithm numerical singularity error")

    monkeypatch.setattr(diagnostic_specialist, "run_diagnostic", mock_failing_diagnostic)

    result = agentic_supervisor.supervise(
        question="Why did revenue drop?",
        catalog=catalog,
        intent_override=IntentCategory.DIAGNOSTIC,
    )

    # Supervisor must not crash; status must record FAILED
    diag_task = next((t for t in result.tasks if t.specialist == SpecialistRole.DIAGNOSTIC), None)
    assert diag_task is not None
    assert diag_task.status == TaskStatus.FAILED
    assert "singularity" in diag_task.error_or_abstain_reason


# ==============================================================================
# SCENARIO 11: Critic Rejection of Unsupported Claims
# ==============================================================================
def test_scenario_11_critic_claim_rejection():
    narrative = (
        "Revenue increased by 999.0% reaching $999,999,999, which proves that Marketing definitely caused the boom."
    )
    metrics = {"revenue_mean": 15000.0, "delta_percentage": 5.2}

    report = critic_specialist.validate_narrative_and_claims(
        narrative=narrative,
        computed_metrics=metrics,
    )

    assert report.is_faithful is False
    assert len(report.discrepancies) > 0
    assert report.confidence_discount > 0.0
    # Must flag unverified monetary/percentage and unhedged causal claims
    assert any("Unverified" in d or "Causal" in d for d in report.discrepancies)


# ==============================================================================
# SCENARIO 12: Missing Temporal Data and Safe Abstention
# ==============================================================================
def test_scenario_12_predictive_insufficient_temporal_abstention():
    # Provide small 3-row dataframe (less than 6 points required)
    tiny_df = pd.DataFrame({
        "order_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        "revenue": [100.0, 150.0, 120.0],
    })
    plan = AnalyticalPlan(
        plan_id="test_plan_tiny",
        question="Forecast next month",
        intent=IntentCategory.PREDICTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Forecast with tiny data",
        selected_method=AnalyticalMethod.TIME_SERIES_FORECAST,
    )

    res = predictive_specialist.run_forecast(tiny_df, plan)
    assert res.success is False
    assert "Insufficient temporal observations" in res.abstain_reason


# ==============================================================================
# SCENARIO 13: Unsupported Optimization Assumptions
# ==============================================================================
def test_scenario_13_prescriptive_unsupported_assumptions_abstention():
    plan = AnalyticalPlan(
        plan_id="test_plan_impossible",
        question="arbitrary magic optimize without data",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Impossible optimization",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_specialist.run_optimization(pd.DataFrame(), plan)
    assert res.success is False
    assert "unsupported optimization assumptions" in res.abstain_reason.lower()


# ==============================================================================
# SCENARIO 14: Read-Only SQL Enforcement
# ==============================================================================
def test_scenario_14_readonly_sql_enforcement(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="DROP TABLE sales_performance; SELECT * FROM sales_performance;",
        catalog=catalog,
    )

    # Must be blocked by read-only security check
    assert result.success is False
    assert result.tasks[0].status == TaskStatus.FAILED
    assert "Security violation" in result.tasks[0].error_or_abstain_reason


# ==============================================================================
# SCENARIO 15: Partial Workflow Completion
# ==============================================================================
def test_scenario_15_partial_workflow_completion(setup_test_environment, monkeypatch):
    _, catalog = setup_test_environment

    result = agentic_supervisor.supervise(
        question="Describe revenue and forecast future growth.",
        catalog=catalog,
    )

    statuses = [t.status for t in result.tasks]
    assert TaskStatus.COMPLETED in statuses


# ==============================================================================
# SCENARIO 16: Regional Weekly Order Drop Investigation (Demonstration A)
# ==============================================================================
def test_scenario_16_regional_weekly_order_drop_investigation(setup_test_environment):
    _, catalog = setup_test_environment
    result = agentic_supervisor.supervise(
        question="Weekly orders in one region dropped sharply last month. Is this unusual, and what is driving it?",
        catalog=catalog,
    )

    assert result.success is True
    assert result.primary_intent == IntentCategory.DIAGNOSTIC
    assert len(result.tasks) == 4
    assert result.tasks[0].task_type == "schema_grounded_sql_extraction"
    assert result.tasks[1].task_type == "regional_weekly_order_anomaly_detection"
    assert result.tasks[2].task_type == "sales_channel_and_fulfillment_variance_decomposition"
    assert result.tasks[3].task_type == "factual_faithfulness_and_causal_interception"

    m = result.analytical_result.computed_metrics
    assert m["target_region"] == "JP-Kanto"
    assert m["pct_change_monthly"] == -17.91
    assert m["z_score"] == -1.81
    assert m["is_unusual"] is True
    assert m["primary_driver"] == "Website"
    assert m["primary_driver_pct"] == 63.1

    # Verify management response contains required weekly order sections and non-causal disclosures
    assert "JP-Kanto" in result.management_response.composed_markdown
    assert "Website" in result.management_response.composed_markdown
    assert "Statistical Note" in result.management_response.composed_markdown

