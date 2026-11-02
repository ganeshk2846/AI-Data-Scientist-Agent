"""
backend/tests/test_phase4_descriptive.py
Unit tests for Generic Descriptive Analytics Engine.
"""

import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, AnalyticalPlan, ComplexityLevel, IntentCategory
from backend.app.analysis.descriptive_engine import descriptive_engine


def test_descriptive_stats_computation():
    """Verifies descriptive statistics calculation (mean, median, IQR, percentiles)."""
    df = pd.DataFrame({"cost": [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]})
    stats = descriptive_engine.compute_descriptive_stats(df, "cost")

    assert stats["count"] == 10
    assert stats["sum"] == 550.0
    assert stats["mean"] == 55.0
    assert stats["median"] == 55.0
    assert stats["min"] == 10.0
    assert stats["max"] == 100.0
    assert stats["iqr"] > 0


def test_trend_analysis_with_growth():
    """Verifies chronological trend calculation and growth rate."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    df = pd.DataFrame({"date": dates, "admissions": [10, 12, 15, 18, 20, 22, 25, 28, 30, 35]})

    trend = descriptive_engine.compute_trend_analysis(df, date_col="date", metric_col="admissions")

    assert len(trend["series"]) == 10
    assert trend["summary"]["overall_growth_pct"] > 0
    assert "increased" in trend["findings"][0]


def test_period_comparison():
    """Verifies period-over-period delta absolute and percentage computation."""
    dates = pd.date_range("2026-01-01", periods=8, freq="D")
    df = pd.DataFrame({"date": dates, "spend": [100.0, 100.0, 100.0, 100.0, 200.0, 200.0, 200.0, 200.0]})

    pop = descriptive_engine.compute_auto_period_comparison(df, date_col="date", metric_col="spend")

    assert pop["metrics"]["period_a_value"] == 400.0
    assert pop["metrics"]["period_b_value"] == 800.0
    assert pop["metrics"]["delta_absolute"] == 400.0
    assert pop["metrics"]["delta_percentage"] == 100.0


def test_category_segmentation():
    """Verifies top-N segmentation and share of total percentages."""
    df = pd.DataFrame({
        "department": ["Cardiology", "Neurology", "Cardiology", "Orthopedics"],
        "cost": [500.0, 300.0, 500.0, 200.0],
    })

    seg = descriptive_engine.compute_segmentation(df, category_col="department", metric_col="cost")

    assert len(seg["segments"]) == 3
    assert seg["segments"][0]["category"] == "Cardiology"
    assert seg["segments"][0]["total_value"] == 1000.0
    assert seg["segments"][0]["share_pct"] == 66.67

