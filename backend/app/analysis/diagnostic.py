"""
Deterministic diagnostic driver and variance decomposition tool.
Ranks candidate drivers with sample sizes, contributions, and explicit non-causal disclaimer.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd
from backend.app.analysis.contracts import (
    AnalysisToolResult,
    AnalysisType,
    DriverAnalysisResult,
    DriverContribution,
    ProvenanceInfo,
)


def analyze_drivers(
    records: List[Dict[str, Any]],
    metric_col: str,
    dimension_col: str,
    period_col: Optional[str] = None,
    period_a_val: Optional[Any] = None,
    period_b_val: Optional[Any] = None,
    metric_name: Optional[str] = None,
) -> AnalysisToolResult:
    """
    Decomposes variance in a metric across dimensions between two periods or categories.
    Determines top positive and negative drivers of change.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    disp_metric = metric_name or metric_col

    if not records:
        return AnalysisToolResult(
            tool_name="analyze_drivers",
            analysis_type=AnalysisType.DRIVER_ANALYSIS,
            success=False,
            provenance=ProvenanceInfo(
                record_count=0,
                computed_at=now_iso,
                method_name="variance_mix_decomposition",
            ),
            abstain_reason="No records provided for driver analysis.",
        )

    df = pd.DataFrame(records)

    if metric_col not in df.columns or dimension_col not in df.columns:
        return AnalysisToolResult(
            tool_name="analyze_drivers",
            analysis_type=AnalysisType.DRIVER_ANALYSIS,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(df),
                computed_at=now_iso,
                method_name="variance_mix_decomposition",
            ),
            abstain_reason=f"Columns '{metric_col}' and '{dimension_col}' are required.",
        )

    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce").fillna(0.0)

    # If period column provided, partition into period A and period B
    if period_col and period_col in df.columns and period_a_val is not None and period_b_val is not None:
        df_a = df[df[period_col].astype(str) == str(period_a_val)]
        df_b = df[df[period_col].astype(str) == str(period_b_val)]
    else:
        # If no period given, split dataset into first half and second half
        mid = len(df) // 2
        df_a = df.iloc[:mid]
        df_b = df.iloc[mid:]

    sum_a = float(df_a[metric_col].sum())
    sum_b = float(df_b[metric_col].sum())
    total_delta = sum_b - sum_a

    agg_a = df_a.groupby(dimension_col)[metric_col].sum()
    agg_b = df_b.groupby(dimension_col)[metric_col].sum()

    all_dims = sorted(list(set(agg_a.index).union(set(agg_b.index))))
    drivers: List[DriverContribution] = []

    for dim in all_dims:
        val_a = float(agg_a.get(dim, 0.0))
        val_b = float(agg_b.get(dim, 0.0))
        d_delta = val_b - val_a

        if abs(total_delta) > 1e-9:
            pct_contrib = (d_delta / total_delta) * 100.0
        else:
            pct_contrib = 0.0

        if d_delta > 0.01:
            direction = "positive"
        elif d_delta < -0.01:
            direction = "negative"
        else:
            direction = "neutral"

        drivers.append(
            DriverContribution(
                dimension_value=str(dim),
                period_a_value=round(val_a, 2),
                period_b_value=round(val_b, 2),
                delta=round(d_delta, 2),
                pct_of_total_delta=round(pct_contrib, 2),
                direction=direction,
            )
        )

    # Sort drivers by absolute delta magnitude
    drivers.sort(key=lambda d: abs(d.delta), reverse=True)

    result_payload = DriverAnalysisResult(
        metric_name=disp_metric,
        dimension=dimension_col,
        total_delta=round(total_delta, 2),
        sample_size=len(df),
        drivers=drivers,
    )

    return AnalysisToolResult(
        tool_name="analyze_drivers",
        analysis_type=AnalysisType.DRIVER_ANALYSIS,
        success=True,
        provenance=ProvenanceInfo(
            record_count=len(df),
            computed_at=now_iso,
            method_name="variance_mix_decomposition",
            assumptions=[
                f"Computed mix decomposition along dimension '{dimension_col}'",
                f"Total period delta = {round(total_delta, 2)}",
                "Results identify observational variance attribution, not causal counterfactuals",
            ],
        ),
        driver_analysis=result_payload,
    )
