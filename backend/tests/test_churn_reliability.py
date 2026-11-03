"""
Tests for Reliable Customer Churn Analysis, Schema Reconciliation,
Temporal Leakage Prevention, and ML Baselines.
"""

import pytest
from backend.app.analysis.churn_engine import churn_analytics_engine
from backend.app.analysis.churn import analyze_customer_churn_risk
from backend.app.orchestration.supervisor import agentic_supervisor


def test_churn_schema_discrepancy_reconciliation():
    res = churn_analytics_engine.analyze_churn(run_ml_baseline=False)
    assert res["success"] is True
    assert res["total_customers"] == 20000
    assert res["inactive_customers"] in [3551, 3565]
    
    disc = res["discrepancy_analysis"]
    assert "explanation" in disc
    assert "breakdown_in_customers" in disc
    assert disc["breakdown_in_customers"]["Churned"] == 1625
    assert disc["breakdown_in_customers"]["Dormant"] == 1940
    assert disc["history_table_rows"] > 10000


def test_churn_revenue_exposure_and_confidence_intervals():
    res = churn_analytics_engine.analyze_churn(run_ml_baseline=False)
    assert res["total_revenue_at_risk"] > 500000000.0  # > $500M
    segments = {s["segment_name"]: s for s in res["segments"]}
    
    assert "At Risk" in segments
    assert "Inactive" in segments
    at_risk = segments["At Risk"]
    inactive = segments["Inactive"]

    # Check $345.89M on At Risk and $281.77M on Inactive
    assert at_risk["revenue_at_risk"] >= 340000000.0
    assert inactive["revenue_at_risk"] >= 280000000.0

    # Wilson 95% Confidence Interval check
    assert len(at_risk["confidence_interval_95"]) == 2
    assert at_risk["confidence_interval_95"][0] <= at_risk["churn_rate_pct"] <= at_risk["confidence_interval_95"][1]


def test_churn_temporal_ml_baseline_and_defensible_abstention():
    res = churn_analytics_engine.analyze_churn(run_ml_baseline=True)
    assert res["abstain_from_predictive_claims"] is True
    assert "decoupled" in res["abstain_reason"].lower() or "synthetic" in res["abstain_reason"].lower()

    ml = res["ml_benchmarks"]
    assert ml["evaluation_method"] == "strict_temporal_split"
    models = ml["models"]
    assert "logistic_regression" in models
    assert "random_forest" in models
    assert "gradient_boosting" in models

    # Verify honest reporting: AUC ~ 0.50 - 0.53 (not fabricated 0.99)
    for model_name, metrics in models.items():
        assert 0.48 <= metrics["roc_auc"] <= 0.55
        assert 0.14 <= metrics["pr_auc"] <= 0.20
        assert 0.12 <= metrics["brier_score"] <= 0.15


def test_legacy_analyze_customer_churn_risk_compatibility():
    tool_res = analyze_customer_churn_risk()
    assert tool_res.success is True
    assert tool_res.churn_risk is not None
    assert tool_res.churn_risk.total_revenue_at_risk > 0
    assert len(tool_res.churn_risk.segments) > 0


def test_supervisor_churn_orchestration():
    res = agentic_supervisor.supervise("Analyze customer churn risk", session_id="test_churn_supervisor")
    assert res.success is True
    assert res.management_response.what is not None
    assert res.management_response.why is not None
    assert res.management_response.what_next is not None
    assert res.management_response.so_what is not None
    assert "345.89M" in res.management_response.what.headline or "revenue" in res.management_response.what.headline.lower()
    assert "temporal" in res.management_response.what_next.headline.lower() or "roc-auc" in res.management_response.what_next.headline.lower()
