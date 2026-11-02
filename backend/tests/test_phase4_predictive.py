"""
backend/tests/test_phase4_predictive.py
Unit tests for Generic Predictive Analytics Engine.
"""

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, AnalyticalPlan, ComplexityLevel, IntentCategory
from backend.app.analysis.predictive_engine import MIN_FORECAST_OBSERVATIONS, compute_smape, predictive_engine


def test_smape_metric_calculation():
    """Verifies symmetric MAPE computation."""
    y_true = np.array([100.0, 200.0])
    y_pred = np.array([110.0, 190.0])
    # |100-110|/105 = 0.0952, |200-190|/195 = 0.05128 -> mean ~ 0.0732 = 7.32%
    smape = compute_smape(y_true, y_pred)
    assert 5.0 < smape < 10.0


def test_forecast_model_selection_and_intervals():
    """Verifies multi-model evaluation and 80%/95% prediction intervals."""
    np.random.seed(42)
    dates = pd.date_range("2026-01-01", periods=25, freq="D")
    vals = 50.0 + np.arange(25) * 1.5 + np.random.normal(0, 1, 25)
    df = pd.DataFrame({"date": dates, "metric": vals})

    res = predictive_engine.forecast_time_series(df, date_col="date", target_col="metric", horizon=7)

    assert res["success"] is True
    assert len(res["forecast_points"]) == 7
    assert res["evaluation_metrics"]["smape_pct"] >= 0.0
    assert res["model_info"]["selected_model"] is not None

    # Check prediction intervals are strictly nested: lower_95 <= lower_80 <= point <= upper_80 <= upper_95
    for p in res["forecast_points"]:
        assert p["lower_bound_95"] <= p["lower_bound_80"]
        assert p["lower_bound_80"] <= p["point_forecast"]
        assert p["point_forecast"] <= p["upper_bound_80"]
        assert p["upper_bound_80"] <= p["upper_bound_95"]


def test_forecast_abstention_on_insufficient_history():
    """Verifies predictive engine cleanly abstains if observations are fewer than MIN_FORECAST_OBSERVATIONS."""
    dates = pd.date_range("2026-01-01", periods=4, freq="D")
    df = pd.DataFrame({"date": dates, "metric": [10.0, 20.0, 30.0, 40.0]})

    plan = AnalyticalPlan(
        plan_id="p_short",
        question="Forecast metric for next week",
        intent=IntentCategory.PREDICTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Forecast",
        selected_method=AnalyticalMethod.TIME_SERIES_FORECAST,
        target_variable="metric",
        time_dimension="date",
    )

    res = predictive_engine.run_predictive_analysis(df, plan)
    assert res.success is False
    assert "Insufficient historical data" in res.abstain_reason

