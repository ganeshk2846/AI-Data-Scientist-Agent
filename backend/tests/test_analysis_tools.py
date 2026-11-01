"""
Comprehensive unit and integration tests for Phase 6 deterministic analysis tools.
Tests reproducible calculations, edge cases, missing data, small sample sizes,
abstain conditions, and typed contracts.
"""

import pytest
from backend.app.analysis.anomalies import detect_anomalies
from backend.app.analysis.churn import analyze_customer_churn_risk
from backend.app.analysis.contracts import AnalysisType
from backend.app.analysis.descriptive import compare_periods
from backend.app.analysis.diagnostic import analyze_drivers
from backend.app.analysis.forecasting import forecast_series
from backend.app.analysis.optimization import optimize_budget_allocation
from backend.app.analysis.registry import analysis_registry
from backend.app.analysis.scenarios import simulate_scenario


def test_compare_periods_calculation():
    records = [
        {"period": "2024", "category": "Electronics", "revenue": 1000.0},
        {"period": "2024", "category": "Apparel", "revenue": 500.0},
        {"period": "2025", "category": "Electronics", "revenue": 1400.0},
        {"period": "2025", "category": "Apparel", "revenue": 600.0},
    ]
    res = compare_periods(
        records,
        metric_col="revenue",
        period_col="period",
        period_a_val="2024",
        period_b_val="2025",
        dimension_col="category",
    )
    assert res.success is True
    assert res.period_comparison is not None
    assert res.period_comparison.period_a_value == 1500.0
    assert res.period_comparison.period_b_value == 2000.0
    assert res.period_comparison.delta_absolute == 500.0
    assert res.period_comparison.delta_percentage == pytest.approx(33.33, 0.1)
    assert len(res.period_comparison.dimension_breakdown) == 2
    # Electronics delta = +400, Apparel delta = +100
    top = res.period_comparison.dimension_breakdown[0]
    assert top["dimension_value"] == "Electronics"
    assert top["delta"] == 400.0
    assert top["pct_of_total_delta"] == 80.0


def test_compare_periods_abstain():
    empty_res = compare_periods([], "rev", "period", "2024", "2025")
    assert empty_res.success is False
    assert "zero records" in empty_res.abstain_reason.lower()


def test_detect_anomalies_and_data_quality_screen():
    # Regular values with one spike and one duplicate jump
    records = [
        {"date": f"2025-01-0{i}", "orders": 100.0 + (i % 3) * 5.0} for i in range(1, 10)
    ]
    # Add a huge spike at day 10
    records.append({"date": "2025-01-10", "orders": 500.0})

    res = detect_anomalies(records, date_col="date", metric_col="orders", threshold=2.5)
    assert res.success is True
    assert res.anomaly_detection is not None
    assert res.anomaly_detection.total_data_points == 10
    assert res.anomaly_detection.anomaly_count >= 1

    spike = [a for a in res.anomaly_detection.anomalies if a.date == "2025-01-10"][0]
    assert spike.is_anomaly is True
    assert spike.severity == "severe"
    assert spike.quality_flag == "suspected_batch_spike_or_duplicate_load"


def test_detect_anomalies_abstain_insufficient_data():
    small_records = [{"date": "2025-01-01", "orders": 100.0}, {"date": "2025-01-02", "orders": 110.0}]
    res = detect_anomalies(small_records, date_col="date", metric_col="orders")
    assert res.success is False
    assert "insufficient observations" in res.abstain_reason.lower()


def test_analyze_drivers_with_non_causal_disclaimer():
    records = [
        {"region": "North", "sales": 100.0, "half": "H1"},
        {"region": "South", "sales": 200.0, "half": "H1"},
        {"region": "North", "sales": 150.0, "half": "H2"},
        {"region": "South", "sales": 180.0, "half": "H2"},
    ]
    res = analyze_drivers(
        records,
        metric_col="sales",
        dimension_col="region",
        period_col="half",
        period_a_val="H1",
        period_b_val="H2",
    )
    assert res.success is True
    assert res.driver_analysis is not None
    assert res.driver_analysis.total_delta == 30.0
    # North drove +50, South drove -20
    north = [d for d in res.driver_analysis.drivers if d.dimension_value == "North"][0]
    assert north.delta == 50.0
    assert north.direction == "positive"
    # Verify strict non-causal disclaimer
    assert "not causal proof" in res.driver_analysis.causal_claim_disclaimer.lower()


def test_forecast_series_intervals_and_backtesting():
    # 20 points of linear series
    records = [{"date": f"2025-01-{i:02d}", "sales": 100.0 + 5.0 * i} for i in range(1, 21)]
    res = forecast_series(records, date_col="date", value_col="sales", horizon_periods=7)
    assert res.success is True
    assert res.forecast is not None
    assert len(res.forecast.points) == 7
    assert res.forecast.is_sufficient_data is True
    assert res.forecast.backtest_mae is not None
    assert res.forecast.backtest_mape_pct is not None
    # Check that intervals widen or hold: lower < point < upper
    pt = res.forecast.points[0]
    assert pt.lower_bound_80 <= pt.point_forecast <= pt.upper_bound_80
    assert pt.lower_bound_95 <= pt.point_forecast <= pt.upper_bound_95


def test_forecast_series_abstain():
    records = [{"date": "2025-01-01", "sales": 100.0}]
    res = forecast_series(records, date_col="date", value_col="sales")
    assert res.success is False
    assert "insufficient historical data" in res.abstain_reason.lower()


def test_simulate_scenario_sensitivities():
    res = simulate_scenario(baseline_value=10000.0, parameter_name="price", shock_pct=5.0, elasticity=-1.5)
    assert res.success is True
    assert res.scenario is not None
    assert res.scenario.baseline_value == 10000.0
    # New revenue = 10000 * (1 + 0.05) * (1 - 0.075) = 10000 * 1.05 * 0.925 = 9712.5
    assert res.scenario.simulated_value == pytest.approx(9712.5, 0.5)
    assert len(res.scenario.sensitivities) == 5


def test_simulate_scenario_abstain():
    res = simulate_scenario(baseline_value=-50.0, parameter_name="price", shock_pct=5.0)
    assert res.success is False
    assert "positive" in res.abstain_reason.lower()


def test_analyze_customer_churn_risk_against_sqlite():
    res = analyze_customer_churn_risk()
    assert res.success is True
    assert res.churn_risk is not None
    assert res.churn_risk.total_customers_analyzed > 0
    assert res.churn_risk.total_revenue_at_risk > 0
    assert len(res.churn_risk.segments) >= 5
    # Segments must be ranked by actionability
    ranks = [s.actionability_rank for s in res.churn_risk.segments]
    assert ranks == list(range(1, len(res.churn_risk.segments) + 1))
    # Wilson CI low <= churn_rate <= Wilson CI high
    for s in res.churn_risk.segments:
        assert s.confidence_interval_low <= s.churn_rate_pct <= s.confidence_interval_high


def test_optimize_budget_allocation():
    channels = ["Paid Search", "Social Media", "Email", "Affiliates"]
    roas = {"Paid Search": 4.0, "Social Media": 3.0, "Email": 5.0, "Affiliates": 2.0}
    res = optimize_budget_allocation(total_budget=10000.0, channels=channels, historical_roas=roas)
    assert res.success is True
    assert res.optimization is not None
    assert sum(res.optimization.allocations.values()) == pytest.approx(10000.0, 1.0)
    # Highest allocation should go to Email (highest ROAS 5.0)
    assert res.optimization.allocations["Email"] > res.optimization.allocations["Affiliates"]


def test_optimize_budget_abstain():
    res = optimize_budget_allocation(total_budget=-100.0, channels=["A", "B"], historical_roas={"A": 1.0, "B": 2.0})
    assert res.success is False
    assert "positive" in res.abstain_reason.lower()


def test_analysis_registry_discovery_and_intent():
    tools = analysis_registry.list_tools()
    assert len(tools) >= 7
    assert analysis_registry.detect_intent("What is the sales forecast for next month?") == "forecast_series"
    assert analysis_registry.detect_intent("Are there any volume anomalies or spikes?") == "detect_anomalies"
    assert analysis_registry.detect_intent("Why did our margin fall?") == "analyze_drivers"
    assert analysis_registry.detect_intent("What is the churn risk for dormant customers?") == "analyze_customer_churn_risk"
    assert analysis_registry.detect_intent("What if price increases by 10%?") == "simulate_scenario"
    assert analysis_registry.detect_intent("Optimize budget across channels") == "optimize_budget_allocation"

