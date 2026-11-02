"""
backend/tests/test_phase4_1_lightgbm_forecast.py
Unit tests for LightGBM Recursive Forecasting and Model Selection.
Verifies that when LightGBM is the winning model, it generates true recursive multi-step
autoregressive projections that differ from a flat persistence baseline.
"""

import math
import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, AnalyticalPlan, ComplexityLevel, IntentCategory
from backend.app.analysis.predictive_engine import predictive_engine


def test_lightgbm_recursive_forecast_produces_dynamic_curve():
    """
    Verifies that LightGBM generates a dynamic multi-step autoregressive projection
    rather than a flat persistence line when selected as champion.
    """
    # High autocorrelation AR(3) series with 100 points where LightGBM excels
    np.random.seed(42)
    n = 100
    series = [100.0, 102.0, 105.0]
    for _ in range(3, n):
        val = 0.6 * series[-1] + 0.3 * series[-2] + 0.1 * series[-3] + np.random.normal(0, 0.5)
        series.append(val)

    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    df = pd.DataFrame({"date": dates, "revenue": series})

    res = predictive_engine.forecast_time_series(df, date_col="date", target_col="revenue", horizon=7)

    assert res["success"] is True
    assert res["model_info"]["selected_model"] == "LightGBM Lagged Regression"

    forecast_points = res["forecast_points"]
    assert len(forecast_points) == 7

    point_forecasts = [p["point_forecast"] for p in forecast_points]

    # Verify that point forecasts are NOT all identical (not flat persistence)
    assert len(set(point_forecasts)) > 1, f"Forecasts were flat: {point_forecasts}"


def test_lightgbm_handles_multiple_horizons():
    """Verifies recursive forecasting works across different forecast horizons (3, 7, 14 steps)."""
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    values = np.linspace(50.0, 150.0, 30) + np.random.RandomState(42).normal(0, 2, 30)
    df = pd.DataFrame({"date": dates, "units": values})

    for h in [3, 7, 14]:
        res = predictive_engine.forecast_time_series(df, date_col="date", target_col="units", horizon=h)
        assert res["success"] is True
        assert len(res["forecast_points"]) == h
        # Verify valid numbers without NaN or Inf
        for pt in res["forecast_points"]:
            assert not math.isnan(pt["point_forecast"])
            assert not math.isinf(pt["point_forecast"])


def test_predictive_abstains_on_insufficient_samples():
    """Verifies clean abstention when sample size is below MIN_FORECAST_OBSERVATIONS (<10)."""
    dates = pd.date_range("2026-01-01", periods=8, freq="D")
    df = pd.DataFrame({"date": dates, "val": [10.0] * 8})

    plan = AnalyticalPlan(
        plan_id="p_short",
        question="Forecast val for next week",
        intent=IntentCategory.PREDICTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Forecast val",
        selected_method=AnalyticalMethod.TIME_SERIES_FORECAST,
        time_dimension="t.date",
        target_variable="t.val",
        relevant_tables=["t"],
    )

    res = predictive_engine.run_predictive_analysis(df, plan)
    assert res.success is False
    assert "Insufficient historical data" in (res.abstain_reason or "")
