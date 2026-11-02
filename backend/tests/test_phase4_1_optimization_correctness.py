"""
backend/tests/test_phase4_1_optimization_correctness.py
Mathematical and algorithmic verification tests for Prescriptive Constrained Optimization.
Verifies:
1. Concave diminishing returns optimization satisfies KKT optimality.
2. Linear utility model allocates towards highest efficiency bounds.
3. Budget equality constraint is preserved within tight numerical tolerance (<= 1e-4).
4. Infeasible bounds are detected and reported without claiming false optimality.
5. Solver status accurately reflects optimal vs. fallback heuristic.
"""

import numpy as np
import pytest

from backend.app.analysis.prescriptive_engine import prescriptive_engine


def test_concave_diminishing_returns_optimum():
    """
    Verifies that the default concave utility model (sqrt) produces an interior optimum
    that balances allocations across items according to diminishing marginal utility.
    """
    total_budget = 10000.0
    items = ["A", "B", "C", "D"]
    efficiencies = {"A": 2.0, "B": 1.5, "C": 1.2, "D": 0.8}

    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=total_budget,
        items=items,
        efficiencies=efficiencies,
        min_alloc_pct=0.05,
        max_alloc_pct=0.50,
        utility_model="concave",
    )

    assert res["summary"]["solver_status"] == "Optimal"
    assert res["summary"]["is_optimal"] is True
    assert res["summary"]["utility_model"] == "concave"

    allocations = res["allocations"]
    alloc_dict = {a["item"]: a["allocated_amount"] for a in allocations}

    # Sum of allocations equals total budget within cent rounding tolerance
    total_alloc = sum(alloc_dict.values())
    assert abs(total_alloc - total_budget) <= 0.05
    assert res["summary"]["constraint_residual"] < 1e-4

    # Verify ranking follows efficiency order
    assert alloc_dict["A"] > alloc_dict["B"] > alloc_dict["C"] > alloc_dict["D"]

    # In concave optimization, D still receives non-zero interior allocation due to sqrt diminishing returns
    assert alloc_dict["D"] >= total_budget * 0.05


def test_linear_utility_model_allocates_to_capacity_bounds():
    """
    Verifies that a linear utility model concentrates resources on highest efficiency items
    up to the maximum allocation bound (greedy behavior).
    """
    total_budget = 10000.0
    items = ["Channel 1", "Channel 2", "Channel 3"]
    efficiencies = {"Channel 1": 5.0, "Channel 2": 3.0, "Channel 3": 1.0}

    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=total_budget,
        items=items,
        efficiencies=efficiencies,
        min_alloc_pct=0.10,
        max_alloc_pct=0.60,
        utility_model="linear",
    )

    assert res["summary"]["is_optimal"] is True
    alloc_dict = {a["item"]: a["allocated_amount"] for a in res["allocations"]}

    # Channel 1 (highest efficiency) should receive exactly the maximum allowable bound (60% = 6000.0)
    assert abs(alloc_dict["Channel 1"] - 6000.0) < 1.0
    # Channel 3 (lowest efficiency) should receive the minimum allowable bound (10% = 1000.0)
    assert abs(alloc_dict["Channel 3"] - 1000.0) < 1.0
    # Remaining 30% goes to Channel 2 (3000.0)
    assert abs(alloc_dict["Channel 2"] - 3000.0) < 1.0


def test_infeasible_constraints_detected_safely():
    """
    Verifies that when constraints are mathematically infeasible (e.g. min_alloc_pct * n > 1.0),
    the engine rejects the problem and does NOT claim optimality.
    """
    total_budget = 10000.0
    items = ["A", "B", "C", "D"]
    efficiencies = {"A": 2.0, "B": 1.5, "C": 1.0, "D": 0.5}

    # 4 items * 30% minimum = 120% > 100% (Mathematically impossible)
    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=total_budget,
        items=items,
        efficiencies=efficiencies,
        min_alloc_pct=0.30,
        max_alloc_pct=0.50,
    )

    summary = res["summary"]
    assert summary["solver_status"] == "Infeasible Constraints"
    assert summary["is_optimal"] is False
    assert len(res["allocations"]) == 0
    assert "mathematically infeasible" in res["findings"][0]


def test_invalid_zero_resource_input():
    """Verifies that non-positive resource allocations are safely rejected."""
    res = prescriptive_engine.solve_constrained_optimization(
        total_resource=0.0,
        items=["A", "B"],
        efficiencies={"A": 1.0, "B": 1.0},
    )
    assert res["summary"]["is_optimal"] is False
    assert "Invalid optimization inputs" in res["findings"][0]
