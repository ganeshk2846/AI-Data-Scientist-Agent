"""
backend/tests/test_phase4_diagnostic.py
Unit tests for Generic Diagnostic Analytics Engine.
"""

import numpy as np
import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, AnalyticalPlan, ComplexityLevel, IntentCategory
from backend.app.analysis.diagnostic_engine import NON_CAUSAL_DISCLAIMER, diagnostic_engine


def test_variance_driver_decomposition():
    """Verifies that driver decomposition ranks the segment with largest absolute change first."""
    df = pd.DataFrame({
        "channel": ["Search", "Social", "Search", "Social"],
        "revenue": [1000.0, 500.0, 1200.0, 100.0],
        "period": ["2026-01-01", "2026-01-01", "2026-01-02", "2026-01-02"],
    })

    decomp = diagnostic_engine.decompose_variance(
        df, metric_col="revenue", dimension_col="channel", period_col="period"
    )

    # Social declined by -400, Search increased by +200 -> Social is largest absolute driver
    assert decomp["summary"]["primary_driver"] == "Social"
    assert decomp["drivers"][0]["dimension_value"] == "Social"
    assert decomp["drivers"][0]["delta"] == -400.0


def test_anomaly_detection_isolation_forest():
    """Verifies Isolation Forest flags an artificial 10x spike anomaly."""
    np.random.seed(42)
    normal_vals = list(np.random.normal(100, 5, 25))
    normal_vals.append(850.0)  # Extreme anomaly
    dates = pd.date_range("2026-01-01", periods=26, freq="D")
    df = pd.DataFrame({"date": dates, "val": normal_vals})

    res = diagnostic_engine.detect_anomalies(df, metric_col="val", date_col="date", method="isolation_forest")

    assert res["summary"]["anomaly_count"] >= 1
    flagged_vals = [a["observed_value"] for a in res["anomalies"]]
    assert 850.0 in flagged_vals


def test_correlation_and_hypothesis_testing():
    """Verifies Pearson and Spearman correlation computation."""
    x = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
    y = [2.1, 3.9, 6.2, 8.1, 9.9, 12.0]
    df = pd.DataFrame({"ad_spend": x, "signups": y})

    res = diagnostic_engine.compute_correlation_and_hypothesis(df, "ad_spend", "signups")

    assert res["metrics"]["pearson_r"] > 0.95
    assert res["metrics"]["association_direction"] == "positive"
    assert res["metrics"]["association_strength"] == "strong"
    # Verify non-causal disclaimer is attached
    assert any("Observational Note" in f for f in res["findings"])

