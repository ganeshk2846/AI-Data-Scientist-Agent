"""
backend/tests/test_phase4_1_2_prescriptive_evidence.py
Targeted test suite for Objective D: Prescriptive Evidence Grounding and Optimization Inputs.
Verifies that:
1. Efficiency coefficients are empirically derived from real computed data aggregations.
2. Engine safely abstains when requested optimization concepts (e.g. treatment delays, marketing channels)
   are missing from the schema, preventing arbitrary hardcoded fallbacks.
3. SciPy SLSQP optimization reports complete mathematical metadata including KKT optimality evidence,
   constraints, decision variables, and budget reconciliation.
"""

from pathlib import Path
import sqlite3
import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    AnalyticalPlan,
    ComplexityLevel,
    IntentCategory,
)
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.analysis.prescriptive_engine import SAFE_BOUNDARY_NOTE, prescriptive_engine
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.service import SchemaService


def test_empirical_efficiency_derivation():
    """Verifies that efficiency weights are computed from actual dataframe groupby aggregations."""
    df = pd.DataFrame({
        "channel": ["Email", "Email", "Search", "Search", "Social", "Social"],
        "revenue": [120.0, 140.0, 300.0, 320.0, 200.0, 220.0],
    })

    plan = AnalyticalPlan(
        plan_id="p_emp",
        question="How should we allocate our $30,000 budget across channel?",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Optimize channel budget",
        relevant_tables=["marketing_spend"],
        target_variable="marketing_spend.revenue",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_engine.run_prescriptive_analysis(df, plan)
    assert res.success is True
    assert "coefficients_source" in res.computed_metrics
    assert "Empirical mean of 'revenue' grouped by 'channel'" in res.computed_metrics["coefficients_source"]
    assert res.computed_metrics["is_optimal"] is True
    assert "KKT" in res.computed_metrics["optimality_evidence"]

    # Search should have highest allocation because mean revenue is 310 vs Social 210 vs Email 130
    allocs = res.result_data
    assert allocs[0]["item"] == "Search"


def test_ecommerce_marketing_missing_evidence_abstention():
    """Verifies safe abstention when marketing channels/campaigns do not exist in the schema."""
    # Orders dataframe lacking marketing channel attributes
    df_orders = pd.DataFrame({
        "order_id": [1, 2, 3, 4],
        "order_date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
        "total_amount": [150.0, 200.0, 75.0, 300.0],
        "order_status": ["delivered", "delivered", "cancelled", "delivered"],
    })

    plan = AnalyticalPlan(
        plan_id="p_mkt",
        question="How should we allocate our $25,000 marketing budget to improve expected revenue?",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Allocate marketing budget",
        relevant_tables=["orders"],
        target_variable="orders.total_amount",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_engine.run_prescriptive_analysis(df_orders, plan)
    # Must safely abstain without fabricating marketing channel effectiveness scores
    assert res.success is False
    assert "marketing channel and campaign performance entities are not present" in (res.abstain_reason or "")
    assert SAFE_BOUNDARY_NOTE in res.uncertainty_notes


def test_healthcare_delay_missing_evidence_abstention():
    """Verifies safe abstention when query requests treatment delay reduction but data only contains cost."""
    df_treatments = pd.DataFrame({
        "treatment_id": [1, 2, 3, 4],
        "treatment_type": ["Surgery", "Therapy", "Surgery", "Diagnostics"],
        "treatment_cost": [5000.0, 1200.0, 4800.0, 800.0],
        "treatment_date": ["2025-01-01", "2025-01-02", "2025-01-03", "2025-01-04"],
    })

    plan = AnalyticalPlan(
        plan_id="p_health",
        question="How could hospital resources be allocated to reduce treatment delays under the available capacity constraints?",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Reduce treatment delays",
        relevant_tables=["treatments"],
        target_variable="treatments.treatment_cost",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_engine.run_prescriptive_analysis(df_treatments, plan)
    # Must safely abstain: cost is not equivalent to delay
    assert res.success is False
    assert "treatment delays" in (res.abstain_reason or "")
    assert "treatment_cost" in (res.abstain_reason or "")


def test_healthcare_delay_supported_optimization():
    """Verifies successful optimization when treatment delay metric is genuinely present."""
    df_delay = pd.DataFrame({
        "department": ["Emergency", "Emergency", "Cardiology", "Cardiology", "Oncology", "Oncology"],
        "delay_minutes": [45.0, 55.0, 20.0, 25.0, 15.0, 10.0],
    })

    plan = AnalyticalPlan(
        plan_id="p_health_ok",
        question="How should we allocate our $50,000 staffing budget across department?",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Allocate staffing budget",
        relevant_tables=["departments"],
        target_variable="departments.delay_minutes",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_engine.run_prescriptive_analysis(df_delay, plan)
    assert res.success is True
    assert res.computed_metrics["is_optimal"] is True
    # Emergency had highest average delay (50 mins) and receives top allocation
    assert res.result_data[0]["item"] == "Emergency"


def test_optimization_mathematical_metadata():
    """Verifies all required mathematical optimization metadata in summary output."""
    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=20000.0,
        items=["Dept A", "Dept B", "Dept C"],
        efficiencies={"Dept A": 3.0, "Dept B": 2.0, "Dept C": 1.0},
        min_alloc_pct=0.10,
        max_alloc_pct=0.60,
    )

    summary = res["summary"]
    assert "objective_function" in summary
    assert "decision_variables" in summary
    assert "coefficients_source" in summary
    assert "constraints" in summary
    assert "constraints_source" in summary
    assert "solver_status" in summary
    assert "optimality_evidence" in summary
    assert "budget_reconciliation" in summary

    recon = summary["budget_reconciliation"]
    assert recon["total_budget"] == 20000.0
    assert abs(recon["total_allocated"] - 20000.0) < 0.01
    assert recon["constraint_residual"] < 1e-4

