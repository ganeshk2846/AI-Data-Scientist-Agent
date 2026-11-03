"""
Tests for Impact Analytics ("So What?") Engine and Statistical Evaluation.
"""

import pandas as pd
import pytest
from backend.app.analysis.impact_engine import impact_analytics_engine
from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.orchestration.supervisor import agentic_supervisor


def test_impact_evaluation_welch_t_test_and_effect_size():
    # Two groups with clear separation
    df = pd.DataFrame({
        "channel": ["Organic"] * 40 + ["Paid Search"] * 40,
        "revenue": [100.0 + i * 2 for i in range(40)] + [200.0 + i * 3 for i in range(40)],
    })
    res = impact_analytics_engine.evaluate_impact(
        df=df,
        metric_col="revenue",
        group_col="channel",
        baseline_group="Organic",
        treatment_group="Paid Search",
    )
    assert res.success is True
    assert res.analytical_type == IntentCategory.DIAGNOSTIC
    m = res.computed_metrics
    assert m["delta_absolute"] > 0
    assert m["monetary_delta"] > 0
    assert m["p_value"] < 0.05
    assert m["is_statistically_significant"] is True
    assert m["is_business_significant"] is True
    assert "High Priority" in m["executive_verdict"]
    assert "confidence_interval_95" in m
    assert m["cohens_d"] != 0.0
    assert len(res.limitations) > 0


def test_impact_small_sample_abstention():
    df_small = pd.DataFrame({
        "channel": ["Organic", "Paid Search"],
        "revenue": [100.0, 150.0],
    })
    res = impact_analytics_engine.evaluate_impact(df_small, metric_col="revenue")
    assert res.success is False
    assert res.abstain_reason is not None
    assert "sample size" in res.abstain_reason.lower()


def test_supervisor_impact_orchestration():
    res = agentic_supervisor.supervise(
        "What was the impact on revenue across customer segments?",
        session_id="test_impact_session",
    )
    assert res.success is True
    assert res.management_response.impact_section is not None
    assert res.management_response.impact_section.title == "IMPACT / SO WHAT"
    assert "Verdict" in res.management_response.impact_section.headline or "Impact" in res.management_response.impact_section.headline
