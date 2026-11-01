"""
Deterministic descriptive and period-over-period comparison tools.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from backend.app.analysis.contracts import (
    AnalysisToolResult,
    AnalysisType,
    PeriodComparisonResult,
    ProvenanceInfo,
)


def compare_periods(
    records: List[Dict[str, Any]],
    metric_col: str,
    period_col: str,
    period_a_val: Any,
    period_b_val: Any,
    dimension_col: Optional[str] = None,
    metric_name: Optional[str] = None,
) -> AnalysisToolResult:
    """
    Computes exact period-over-period differences and dimension mix breakdown.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    disp_metric = metric_name or metric_col

    if not records:
        return AnalysisToolResult(
            tool_name="compare_periods",
            analysis_type=AnalysisType.PERIOD_COMPARISON,
            success=False,
            provenance=ProvenanceInfo(
                record_count=0,
                computed_at=now_iso,
                method_name="deterministic_variance_comparison",
                assumptions=["No records provided for period comparison"],
            ),
            abstain_reason="Input data contains zero records to compare.",
        )

    df = pd.DataFrame(records)

    if metric_col not in df.columns or period_col not in df.columns:
        return AnalysisToolResult(
            tool_name="compare_periods",
            analysis_type=AnalysisType.PERIOD_COMPARISON,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(df),
                computed_at=now_iso,
                method_name="deterministic_variance_comparison",
            ),
            abstain_reason=f"Required columns '{metric_col}' or '{period_col}' not found in records.",
        )

    # Cast to numeric safely
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce").fillna(0.0)

    # Split periods
    df_a = df[df[period_col].astype(str) == str(period_a_val)]
    df_b = df[df[period_col].astype(str) == str(period_b_val)]

    if len(df_a) == 0 and len(df_b) == 0:
        return AnalysisToolResult(
            tool_name="compare_periods",
            analysis_type=AnalysisType.PERIOD_COMPARISON,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(df),
                computed_at=now_iso,
                method_name="deterministic_variance_comparison",
            ),
            abstain_reason=f"Neither period '{period_a_val}' nor '{period_b_val}' found in column '{period_col}'.",
        )

    val_a = float(df_a[metric_col].sum())
    val_b = float(df_b[metric_col].sum())
    delta_abs = val_b - val_a
    delta_pct = (delta_abs / val_a * 100.0) if val_a != 0.0 else (100.0 if val_b > 0 else 0.0)

    breakdown: List[Dict[str, Any]] = []
    if dimension_col and dimension_col in df.columns:
        agg_a = df_a.groupby(dimension_col)[metric_col].sum()
        agg_b = df_b.groupby(dimension_col)[metric_col].sum()
        all_dims = sorted(list(set(agg_a.index).union(set(agg_b.index))))

        for dim in all_dims:
            d_val_a = float(agg_a.get(dim, 0.0))
            d_val_b = float(agg_b.get(dim, 0.0))
            d_delta = d_val_b - d_val_a
            d_pct_contrib = (d_delta / delta_abs * 100.0) if abs(delta_abs) > 1e-9 else 0.0
            breakdown.append(
                {
                    "dimension_value": str(dim),
                    "period_a_value": round(d_val_a, 2),
                    "period_b_value": round(d_val_b, 2),
                    "delta": round(d_delta, 2),
                    "pct_of_total_delta": round(d_pct_contrib, 2),
                }
            )
        # Sort by absolute impact descending
        breakdown.sort(key=lambda x: abs(x["delta"]), reverse=True)

    result_data = PeriodComparisonResult(
        metric_name=disp_metric,
        period_a_label=str(period_a_val),
        period_a_value=round(val_a, 2),
        period_b_label=str(period_b_val),
        period_b_value=round(val_b, 2),
        delta_absolute=round(delta_abs, 2),
        delta_percentage=round(delta_pct, 2),
        dimension_breakdown=breakdown,
    )

    return AnalysisToolResult(
        tool_name="compare_periods",
        analysis_type=AnalysisType.PERIOD_COMPARISON,
        success=True,
        provenance=ProvenanceInfo(
            record_count=len(df),
            computed_at=now_iso,
            method_name="deterministic_period_variance",
            assumptions=[
                f"Aggregated metric '{metric_col}' by summing values",
                f"Filtered period '{period_col}' == '{period_a_val}' and '{period_b_val}'",
            ],
        ),
        period_comparison=result_data,
    )

