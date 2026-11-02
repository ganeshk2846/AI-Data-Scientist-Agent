"""
backend/tests/test_phase4_prescriptive.py
Unit tests for Generic Prescriptive Analytics Engine.
"""

import pandas as pd
import pytest

from backend.app.analysis.contracts_v2 import AnalyticalMethod, AnalyticalPlan, ComplexityLevel, IntentCategory
from backend.app.analysis.prescriptive_engine import SAFE_BOUNDARY_NOTE, prescriptive_engine


def test_constrained_optimization_solver():
    """Verifies SciPy optimization satisfies budget sum equality and bound constraints."""
    total_budget = 50000.0
    channels = ["Paid Search", "Paid Social", "Email"]
    efficiencies = {"Paid Search": 4.0, "Paid Social": 2.5, "Email": 1.5}

    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=total_budget,
        items=channels,
        efficiencies=efficiencies,
        min_alloc_pct=0.10,
        max_alloc_pct=0.60,
    )

    allocations = res["allocations"]
    assert len(allocations) == 3

    # Budget equality constraint check: sum(allocated) == total_budget
    total_allocated = sum(a["allocated_amount"] for a in allocations)
    assert abs(total_allocated - total_budget) < 1.0

    # Bounds check: each channel allocated between 10% and 60%
    for a in allocations:
        assert 5000.0 <= a["allocated_amount"] <= 30000.0

    # Highest efficiency channel receives largest allocation
    assert allocations[0]["item"] == "Paid Search"


def test_what_if_scenario_simulation():
    """Verifies parameter shock simulation and sensitivity table."""
    sim = prescriptive_engine.simulate_what_if_scenario(
        baseline_value=100000.0, parameter_name="Price", shock_pct=10.0, elasticity=-1.0
    )

    metrics = sim["metrics"]
    # Baseline: 100k, P * 1.10, Q * 0.90 -> 100k * 0.99 = 99k
    assert metrics["baseline_value"] == 100000.0
    assert metrics["simulated_value"] == 99000.0
    assert metrics["delta_absolute"] == -1000.0
    assert metrics["delta_percentage"] == -1.0

    # Sensitivities span -15% to +15%
    shocks = [s["shock_pct"] for s in sim["sensitivities"]]
    assert -15.0 in shocks and 15.0 in shocks


def test_safe_recommendation_boundary():
    """Verifies that all prescriptive outputs attach the mandatory safe recommendation boundary note."""
    plan = AnalyticalPlan(
        plan_id="p_presc",
        question="What should we do to allocate our $20k budget?",
        intent=IntentCategory.PRESCRIPTIVE,
        complexity=ComplexityLevel.ADVANCED,
        analytical_objective="Optimize budget",
        selected_method=AnalyticalMethod.CONSTRAINED_OPTIMIZATION,
    )

    res = prescriptive_engine.run_prescriptive_analysis(pd.DataFrame(), plan)

    assert res.success is True
    assert len(res.recommended_next_steps) > 0
    assert any("Safe Recommendation Boundary" in u for u in res.uncertainty_notes)

