"""
Tests for Scenario Analytics ("What-If?") Engine and Orchestration Integration.
"""

import pytest
from backend.app.analysis.scenario_engine import scenario_analytics_engine
from backend.app.analysis.contracts_v2 import IntentCategory
from backend.app.orchestration.supervisor import agentic_supervisor


def test_scenario_parameter_parsing():
    params = scenario_analytics_engine.parse_scenario_parameters("What if we increase product prices by 5%?")
    assert params["parameter"] == "price"
    assert params["shock_pct"] == 5.0
    assert params["base_elasticity"] == -1.0
    assert params["target_metric"] == "revenue"

    params_down = scenario_analytics_engine.parse_scenario_parameters("What if demand decreases by 15%?")
    assert params_down["parameter"] == "demand"
    assert params_down["shock_pct"] == -15.0


def test_scenario_simulation_execution():
    res = scenario_analytics_engine.run_scenario_analysis("What if we increase product prices by 5%?")
    assert res.success is True
    assert res.analytical_type == IntentCategory.PRESCRIPTIVE
    assert "baseline_value" in res.computed_metrics
    assert res.computed_metrics["baseline_value"] > 0
    assert "scenarios" in res.computed_metrics
    assert set(res.computed_metrics["scenarios"].keys()) == {"Conservative", "Moderate", "Aggressive"}
    assert "sensitivity_matrix" in res.computed_metrics
    assert len(res.computed_metrics["sensitivity_matrix"]) >= 5
    assert len(res.uncertainty_notes) > 0


def test_scenario_defensive_abstention_on_unsupported_domain():
    res = scenario_analytics_engine.run_scenario_analysis("What happens if we open two additional stores?")
    assert res.success is False
    assert res.abstain_reason is not None
    assert "retail stores" in res.abstain_reason.lower() or "store" in res.abstain_reason.lower()


def test_supervisor_scenario_orchestration():
    res = agentic_supervisor.supervise("What if we increase product prices by 5%?", session_id="test_scen_session")
    assert res.success is True
    assert res.management_response.scenario_section is not None
    assert res.management_response.scenario_section.title == "SCENARIO / WHAT IF"
    assert res.management_response.so_what is not None
    assert "price" in res.management_response.scenario_section.headline.lower() or "revenue" in res.management_response.scenario_section.headline.lower()
