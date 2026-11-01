"""
Deterministic what-if and scenario simulation tool.
Simulates parameter shocks with explicit elasticity assumptions and sensitivity matrices.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.analysis.contracts import (
    AnalysisToolResult,
    AnalysisType,
    ProvenanceInfo,
    ScenarioResult,
)


def simulate_scenario(
    baseline_value: float,
    parameter_name: str,
    shock_pct: float,
    elasticity: float = -1.0,
    target_metric: str = "revenue",
) -> AnalysisToolResult:
    """
    Simulates the impact of a parameter shock (e.g., price increase of +5%)
    on a target metric (e.g., units sold or total revenue) using explicit elasticity assumptions
    and sensitivity bounds.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    if baseline_value <= 0:
        return AnalysisToolResult(
            tool_name="simulate_scenario",
            analysis_type=AnalysisType.SCENARIO,
            success=False,
            provenance=ProvenanceInfo(
                record_count=1,
                computed_at=now_iso,
                method_name="elasticity_scenario_simulation",
            ),
            abstain_reason=f"Baseline value ({baseline_value}) must be positive to simulate scenario percentage shocks.",
        )

    # If price shock on revenue:
    # Revenue = Price * Quantity
    # delta_Q_pct = elasticity * delta_P_pct
    # New_P = P * (1 + shock_pct/100)
    # New_Q = Q * (1 + delta_Q_pct/100)
    # New_Rev = New_P * New_Q = Base_Rev * (1 + shock_pct/100) * (1 + elasticity * shock_pct/100)
    p_factor = 1.0 + (shock_pct / 100.0)
    q_factor = 1.0 + (elasticity * shock_pct / 100.0)

    if target_metric.lower() in ["revenue", "sales", "gross_revenue"]:
        simulated_val = max(0.0, baseline_value * p_factor * q_factor)
    elif target_metric.lower() in ["units", "orders", "volume", "quantity"]:
        simulated_val = max(0.0, baseline_value * q_factor)
    else:
        # Direct linear elasticity
        simulated_val = max(0.0, baseline_value * (1.0 + elasticity * shock_pct / 100.0))

    delta_abs = simulated_val - baseline_value
    delta_pct = (delta_abs / baseline_value) * 100.0

    # Sensitivity bounds across varying elasticities
    sensitivity_steps = [
        round(elasticity * 0.5, 2),
        round(elasticity * 0.75, 2),
        round(elasticity, 2),
        round(elasticity * 1.25, 2),
        round(elasticity * 1.5, 2),
    ]

    sensitivities: List[Dict[str, Any]] = []
    for test_e in sensitivity_steps:
        t_q_factor = 1.0 + (test_e * shock_pct / 100.0)
        if target_metric.lower() in ["revenue", "sales", "gross_revenue"]:
            t_sim = max(0.0, baseline_value * p_factor * t_q_factor)
        else:
            t_sim = max(0.0, baseline_value * t_q_factor)
        t_delta_pct = ((t_sim - baseline_value) / baseline_value) * 100.0

        sensitivities.append(
            {
                "elasticity": test_e,
                "simulated_value": round(t_sim, 2),
                "delta_pct": round(t_delta_pct, 2),
            }
        )

    result_payload = ScenarioResult(
        target_metric=target_metric,
        baseline_value=round(baseline_value, 2),
        simulated_value=round(simulated_val, 2),
        delta_absolute=round(delta_abs, 2),
        delta_percentage=round(delta_pct, 2),
        assumptions_applied={
            "parameter_shocked": parameter_name,
            "shock_pct": shock_pct,
            "base_elasticity": elasticity,
            "relationship_model": "log_log_multiplicative_elasticity",
        },
        sensitivities=sensitivities,
    )

    return AnalysisToolResult(
        tool_name="simulate_scenario",
        analysis_type=AnalysisType.SCENARIO,
        success=True,
        provenance=ProvenanceInfo(
            record_count=1,
            computed_at=now_iso,
            method_name="elasticity_scenario_simulation",
            assumptions=[
                f"Shock of {shock_pct}% applied to parameter '{parameter_name}'",
                f"Assumed base elasticity = {elasticity}",
                "Assumes ceteris paribus (all other market factors remain constant)",
            ],
        ),
        scenario=result_payload,
    )

