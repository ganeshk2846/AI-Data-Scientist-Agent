"""
backend/tests/test_phase4_1_prediction_intervals.py
Unit tests for Prediction Interval Reliability and Boundary Handling.
Verifies:
1. Target metrics allowing negative values (e.g., net profit, delta, loss) preserve negative lower bounds.
2. Volume metrics (e.g., unit counts, orders) clamp lower bounds to zero.
3. Empirical coverage is recorded on validation split.
"""

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.predictive_engine import predictive_engine


def test_intervals_preserve_negative_bounds_for_financial_loss_or_profit():
    """
    Verifies that when target is a metric permitting negative values (e.g. net_profit),
    the lower prediction interval bounds are NOT artificially clamped to zero.
    """
    dates = pd.date_range("2026-01-01", periods=25, freq="D")
    # Low values around zero that dip into negative territory
    values = np.array([5.0, 3.0, 1.0, -2.0, -4.0, -1.0, 2.0] * 3 + [0.0, -3.0, -5.0, 1.0])[:25]
    df = pd.DataFrame({"date": dates, "net_profit": values})

    res = predictive_engine.forecast_time_series(df, date_col="date", target_col="net_profit", horizon=5)

    assert res["success"] is True
    assert res["model_info"]["negative_values_permitted"] is True

    forecast_points = res["forecast_points"]
    # At least one lower bound should be negative since baseline dips around zero with variance
    has_negative_lower_bound = any(p["lower_bound_95"] < 0.0 for p in forecast_points)
    assert has_negative_lower_bound is True, f"Lower bounds were unexpectedly clamped to zero: {forecast_points}"


def test_intervals_clamp_non_negative_for_volume_metrics():
    """
    Verifies that volume metrics (e.g. book checkout counts) with non-negative history
    do not produce negative lower prediction bounds.
    """
    dates = pd.date_range("2026-01-01", periods=25, freq="D")
    values = np.linspace(10.0, 30.0, 25)
    df = pd.DataFrame({"date": dates, "book_loans_count": values})

    res = predictive_engine.forecast_time_series(df, date_col="date", target_col="book_loans_count", horizon=5)

    assert res["success"] is True
    assert res["model_info"]["negative_values_permitted"] is False

    forecast_points = res["forecast_points"]
    for p in forecast_points:
        assert p["lower_bound_80"] >= 0.0
        assert p["lower_bound_95"] >= 0.0


def test_empirical_interval_coverage_recorded():
    """Verifies empirical coverage metrics (80% and 95%) are calculated and recorded."""
    dates = pd.date_range("2026-01-01", periods=30, freq="D")
    values = np.linspace(100.0, 200.0, 30) + np.random.RandomState(42).normal(0, 3, 30)
    df = pd.DataFrame({"date": dates, "revenue": values})

    res = predictive_engine.forecast_time_series(df, date_col="date", target_col="revenue", horizon=5)

    assert res["success"] is True
    model_info = res["model_info"]
    assert "empirical_coverage_80" in model_info
    assert "empirical_coverage_95" in model_info
    assert 0.0 <= model_info["empirical_coverage_80"] <= 100.0
    assert 0.0 <= model_info["empirical_coverage_95"] <= 100.0
    assert "uncertainty_method" in model_info

