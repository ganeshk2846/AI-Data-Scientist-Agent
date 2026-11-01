"""
Deterministic prescriptive optimization tool using scipy.optimize.
Allocates resource budgets across channels or campaigns to maximize expected return
under linear constraints and diminishing returns.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
from scipy.optimize import minimize
from backend.app.analysis.contracts import (
    AnalysisToolResult,
    AnalysisType,
    OptimizationResult,
    ProvenanceInfo,
)


def optimize_budget_allocation(
    total_budget: float,
    channels: List[str],
    historical_roas: Dict[str, float],
    min_allocation_pct: float = 0.05,
    max_allocation_pct: float = 0.50,
) -> AnalysisToolResult:
    """
    Solves a constrained convex optimization problem allocating a fixed budget
    across marketing channels with concave diminishing returns to maximize expected revenue.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if total_budget <= 0:
        return AnalysisToolResult(
            tool_name="optimize_budget_allocation",
            analysis_type=AnalysisType.OPTIMIZATION,
            success=False,
            provenance=ProvenanceInfo(
                record_count=0,
                computed_at=now_iso,
                method_name="scipy_slsqp_optimization",
            ),
            abstain_reason="Total budget must be strictly positive (greater than 0).",
        )

    if not channels or len(channels) < 2:
        return AnalysisToolResult(
            tool_name="optimize_budget_allocation",
            analysis_type=AnalysisType.OPTIMIZATION,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(channels) if channels else 0,
                computed_at=now_iso,
                method_name="scipy_slsqp_optimization",
            ),
            abstain_reason="Optimization requires at least two channels/decision variables to allocate across.",
        )

    n = len(channels)
    roas_vec = np.array([historical_roas.get(ch, 1.0) for ch in channels], dtype=float)

    # Initial equal allocation
    x0 = np.full(n, total_budget / n)

    # Diminishing returns parameter alpha
    alpha = 0.00005

    # Objective: Minimize negative revenue (Maximize revenue)
    # Revenue = sum(roas_i * x_i - alpha * x_i^2)
    def objective(x):
        return -float(np.sum(roas_vec * x - alpha * (x**2)))

    # Constraints: sum(x) == total_budget
    constraints = [{"type": "eq", "fun": lambda x: np.sum(x) - total_budget}]

    # Bounds: min_budget <= x_i <= max_budget
    min_b = total_budget * min_allocation_pct
    max_b = total_budget * max_allocation_pct
    bounds = [(min_b, max_b) for _ in range(n)]

    opt_res = minimize(
        objective,
        x0,
        method="SLSQP",
        bounds=bounds,
        constraints=constraints,
        options={"maxiter": 200, "ftol": 1e-6},
    )

    allocations: Dict[str, float] = {}
    if opt_res.success:
        alloc_sol = opt_res.x
    else:
        # Fallback to proportional allocation
        roas_sum = np.sum(roas_vec) if np.sum(roas_vec) > 0 else n
        alloc_sol = (roas_vec / roas_sum) * total_budget

    expected_rev = float(np.sum(roas_vec * alloc_sol - alpha * (alloc_sol**2)))

    for i, ch in enumerate(channels):
        allocations[ch] = round(float(alloc_sol[i]), 2)

    notes = [
        f"Objective: Maximize return = sum(ROAS_i * x_i - alpha * x_i^2)",
        f"Enforced channel bounds: [{min_allocation_pct*100:.0f}%, {max_allocation_pct*100:.0f}%] of total budget",
        f"Optimization status: {opt_res.message if hasattr(opt_res, 'message') else 'Converged'}",
    ]

    result_payload = OptimizationResult(
        objective="maximize_revenue_under_diminishing_returns",
        total_budget=round(total_budget, 2),
        allocations=allocations,
        expected_total_revenue=round(expected_rev, 2),
        constraints_satisfied=bool(opt_res.success),
        status="converged" if opt_res.success else "fallback_proportional",
        notes=notes,
    )

    return AnalysisToolResult(
        tool_name="optimize_budget_allocation",
        analysis_type=AnalysisType.OPTIMIZATION,
        success=True,
        provenance=ProvenanceInfo(
            record_count=n,
            computed_at=now_iso,
            method_name="scipy_slsqp_optimization",
            assumptions=[
                f"Historical ROAS values: {dict(zip(channels, [round(r, 2) for r in roas_vec]))}",
                f"Alpha diminishing returns curvature parameter = {alpha}",
                f"Budget conservation constraint sum(x) = ${total_budget:,.2f}",
            ],
        ),
        optimization=result_payload,
    )

