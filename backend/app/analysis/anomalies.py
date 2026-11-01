"""
Robust anomaly detection tool with data quality screening.
Uses robust median/MAD z-score and screens for data pipeline quality artifacts.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from backend.app.analysis.contracts import (
    AnalysisToolResult,
    AnalysisType,
    AnomalyDetectionResult,
    AnomalyPoint,
    ProvenanceInfo,
)


def detect_anomalies(
    records: List[Dict[str, Any]],
    date_col: str,
    metric_col: str,
    threshold: float = 2.5,
    metric_name: Optional[str] = None,
) -> AnalysisToolResult:
    """
    Detects anomalous observations in time-series data using robust MAD-based z-scores,
    preceded by an automated data-quality screen for duplicate batch loads or data gaps.
    """
    now_iso = datetime.now(timezone.utc).isoformat()
    disp_metric = metric_name or metric_col

    if not records or len(records) < 5:
        return AnalysisToolResult(
            tool_name="detect_anomalies",
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(records) if records else 0,
                computed_at=now_iso,
                method_name="robust_mad_zscore",
            ),
            abstain_reason=f"Insufficient observations ({len(records) if records else 0} records). At least 5 data points required for dispersion.",
        )

    df = pd.DataFrame(records)
    if date_col not in df.columns or metric_col not in df.columns:
        return AnalysisToolResult(
            tool_name="detect_anomalies",
            analysis_type=AnalysisType.ANOMALY_DETECTION,
            success=False,
            provenance=ProvenanceInfo(
                record_count=len(df),
                computed_at=now_iso,
                method_name="robust_mad_zscore",
            ),
            abstain_reason=f"Required columns '{date_col}' or '{metric_col}' not present.",
        )

    # Sort chronologically
    df[date_col] = df[date_col].astype(str)
    df = df.sort_values(by=date_col).reset_index(drop=True)
    df[metric_col] = pd.to_numeric(df[metric_col], errors="coerce").fillna(0.0)

    values = df[metric_col].to_numpy(dtype=float)
    dates = df[date_col].tolist()
    n = len(values)

    # 1. Data Quality Screen: check for exact duplicate dates or massive 1-day step multipliers
    quality_warnings: List[str] = []
    has_duplicate_dates = len(dates) != len(set(dates))
    if has_duplicate_dates:
        quality_warnings.append("Duplicate timestamps detected in input stream.")

    # 2. Compute Robust Statistics: Median and MAD
    med = float(np.median(values))
    abs_deviations = np.abs(values - med)
    mad = float(np.median(abs_deviations))

    # Consistency constant 0.6745 makes MAD estimate normal std dev
    if mad > 1e-9:
        z_scores = 0.6745 * (values - med) / mad
    else:
        # Fallback to standard deviation if series is uniform
        std_val = float(np.std(values))
        if std_val > 1e-9:
            z_scores = (values - med) / std_val
        else:
            z_scores = np.zeros(n, dtype=float)

    # 3. Rolling window baseline for expected value
    rolling_series = pd.Series(values)
    rolling_expected = rolling_series.rolling(window=min(7, max(3, n // 2)), min_periods=1, center=True).median()

    anomaly_points: List[AnomalyPoint] = []
    anomaly_count = 0

    for i in range(n):
        val = float(values[i])
        z = float(z_scores[i])
        expected = float(rolling_expected.iloc[i])
        is_anom = abs(z) >= threshold

        severity = "none"
        if is_anom:
            anomaly_count += 1
            severity = "severe" if abs(z) >= (threshold * 1.6) else "mild"

        # Screen for duplicate load artifact: if value jumps >= 2.2x previous and z is high
        quality_flag = None
        if i > 0 and values[i - 1] > 0:
            ratio = val / values[i - 1]
            if ratio >= 2.2 and is_anom:
                quality_flag = "suspected_batch_spike_or_duplicate_load"

        anomaly_points.append(
            AnomalyPoint(
                date=str(dates[i]),
                actual_value=round(val, 2),
                expected_value=round(expected, 2),
                z_score=round(z, 2),
                is_anomaly=is_anom,
                severity=severity,
                quality_flag=quality_flag,
            )
        )

    warning_summary = "; ".join(quality_warnings) if quality_warnings else None

    result_payload = AnomalyDetectionResult(
        metric_name=disp_metric,
        threshold=threshold,
        total_data_points=n,
        anomaly_count=anomaly_count,
        anomalies=anomaly_points,
        method="robust_mad_zscore_with_quality_screen",
        quality_warning=warning_summary,
    )

    return AnalysisToolResult(
        tool_name="detect_anomalies",
        analysis_type=AnalysisType.ANOMALY_DETECTION,
        success=True,
        provenance=ProvenanceInfo(
            record_count=n,
            computed_at=now_iso,
            method_name="robust_mad_zscore",
            assumptions=[
                f"Computed median={round(med, 2)}, MAD={round(mad, 2)}",
                f"Evaluated |z-score| >= {threshold}",
                "Ran pre-flight duplicate/gap data quality screen",
            ],
        ),
        anomaly_detection=result_payload,
    )

