"""
backend/tests/test_final_validation_safeguards.py
Final System Validation & Benchmarking Regression Tests.
Verifies:
1. Multi-table JOIN extraction does not corrupt queries with 3rd-table columns.
2. Diagnostic anomaly and variance decomposition gracefully handle non-numeric/missing target columns without KeyError.
3. Predictive time series forecasting handles duplicate column names from multi-table joins.
4. Prescriptive SLSQP optimization gracefully coerces target columns before computing groupby mean.
5. End-to-end multi-agent orchestration for Scenario A (Regional Weekly Drop) and Scenario B (Customer Churn).
"""

import pandas as pd
import pytest
from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    AnalyticalPlan,
    ComplexityLevel,
    IntentCategory,
)
from backend.app.analysis.data_extractor import analytical_data_extractor
from backend.app.analysis.diagnostic_engine import diagnostic_engine
from backend.app.analysis.predictive_engine import predictive_engine
from backend.app.analysis.prescriptive_engine import prescriptive_engine
from backend.app.db.connection import db_manager
from backend.app.orchestration.supervisor import AgenticSupervisor
from backend.app.schema.service import schema_service


@pytest.fixture(scope="module", autouse=True)
def setup_db():
    db_manager.initialize()


def test_join_extraction_filters_foreign_tables():
    """Verify that multi-table JOIN synthesis does not select columns from third tables."""
    cat = schema_service.get_cached_catalog()
    assert cat is not None

    # Plan has primary table 'order_items' and secondary 'orders', but time_dimension from 'order_status_history'
    plan = AnalyticalPlan(
        plan_id="test_join_plan",
        question="Show order item quantities over time",
        intent=IntentCategory.DESCRIPTIVE,
        complexity=ComplexityLevel.MODERATE,
        analytical_objective="Analyze order items trend across joined orders table",
        selected_method=AnalyticalMethod.METRIC_AGGREGATION,
        relevant_tables=["order_items", "orders"],
        target_variable="order_items.quantity",
        time_dimension="order_status_history.status_timestamp",  # 3rd table!
    )

    sql = analytical_data_extractor._synthesize_extraction_sql(plan, cat)
    assert sql is not None
    assert "order_status_history" not in sql
    assert "order_items" in sql
    assert "orders" in sql

    # Executing the SQL should succeed without column errors
    success, df, queries, err = analytical_data_extractor.extract_data_for_plan(plan, catalog=cat)
    assert success is True
    assert df is not None
    assert len(df) > 0


def test_diagnostic_engine_graceful_on_missing_numeric_column():
    """Verify that diagnostic engine abstains gracefully when no numeric target column exists."""
    plan = AnalyticalPlan(
        plan_id="test_diag_plan",
        question="Why did categories change?",
        intent=IntentCategory.DIAGNOSTIC,
        complexity=ComplexityLevel.COMPLEX,
        analytical_objective="Diagnose category textual changes",
        selected_method=AnalyticalMethod.ANOMALY_DETECTION,
        relevant_tables=["categories"],
        target_variable=None,
    )

    # DataFrame with purely text columns
    text_df = pd.DataFrame({
        "category_name": ["Electronics", "Books", "Home"],
        "category_desc": ["Gadgets", "Literature", "Furniture"],
    })

    res = diagnostic_engine.run_diagnostic_analysis(text_df, plan)
    assert res.success is False
    assert res.abstain_reason is not None
    assert "no numeric metric column" in res.abstain_reason.lower()


def test_predictive_engine_handles_duplicate_column_names():
    """Verify that predictive forecasting handles multi-table join dataframes with duplicate column names."""
    # Create DataFrame with duplicate 'order_date' column names
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    df = pd.DataFrame({
        "order_date": dates,
        "total_amount": [100.0 + i * 2.0 for i in range(30)],
    })
    # Artificially duplicate the date column to simulate multi-table join
    df_dup = pd.concat([df, df[["order_date"]]], axis=1)
    assert df_dup.columns.tolist().count("order_date") == 2

    res = predictive_engine.forecast_time_series(df_dup, date_col="order_date", target_col="total_amount", horizon=7)
    assert res["success"] is True
    assert "forecast_points" in res
    assert len(res["forecast_points"]) == 7


def test_prescriptive_engine_handles_coercible_numeric_targets():
    """Verify that prescriptive engine safely coerces string numbers before computing groupby mean."""
    plan = AnalyticalPlan(
        plan_id="test_presc_plan",
        question="Optimize budget allocation across categories with $100000",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.COMPLEX,
        analytical_objective="Optimize resource allocation across category pricing tiers",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
        relevant_tables=["categories", "products"],
        target_variable="price",
    )

    # DataFrame where target variable is stored as string formatted numbers
    df = pd.DataFrame({
        "category": ["Electronics", "Electronics", "Clothing", "Clothing", "Books", "Books"] * 10,
        "price": ["120.50", "340.00", "45.00", "89.90", "15.00", "22.50"] * 10,
    })

    res = prescriptive_engine.run_prescriptive_analysis(df, plan)
    assert res.success is True
    assert len(res.findings) > 0
    assert res.computed_metrics.get("is_optimal") is True
    assert res.computed_metrics.get("total_budget") == 100000.0


def test_supervisor_scenario_a_regional_weekly_order_drop():
    """Scenario A: Weekly orders in one region dropped sharply last month."""
    sup = AgenticSupervisor()
    qA = "Weekly orders in one region dropped sharply last month. Is this unusual, and what is driving it?"
    resA = sup.supervise(qA)

    assert resA.success is True
    assert resA.management_response is not None
    assert len(resA.tasks) >= 3
    # Check that critic validated claims
    critic_task = next((t for t in resA.tasks if t.specialist.value == "CRITIC"), None)
    assert critic_task is not None
    assert critic_task.status.value == "COMPLETED"


def test_supervisor_scenario_b_churn_prioritization():
    """Scenario B: Which customer segments are we most likely to lose next quarter, and where should we act first?"""
    sup = AgenticSupervisor()
    qB = "Which customer segments are we most likely to lose next quarter, and where should we act first?"
    resB = sup.supervise(qB)

    assert resB.success is True
    assert resB.management_response is not None
    assert len(resB.tasks) >= 3
