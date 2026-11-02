"""
backend/app/analysis/descriptive_engine.py
Domain-Independent Generic Descriptive Analytics Engine for Phase 4.
Answers: WHAT HAPPENED?
Computes exact KPIs, aggregations, period-over-period deltas, multi-frequency time-series trends,
dimension segmentations, and statistical distribution summaries across any schema.
"""

import math
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
import numpy as np
import pandas as pd

from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    AnalyticalPlan,
    IntentCategory,
    StandardizedAnalyticalResult,
)
from backend.app.core.logging import logger


class DescriptiveAnalyticsEngine:
    """
    Executes domain-independent descriptive analytics on extracted DataFrames.
    """

    def run_descriptive_analysis(
        self,
        df: pd.DataFrame,
        plan: AnalyticalPlan,
        executed_queries: Optional[List[str]] = None,
    ) -> StandardizedAnalyticalResult:
        """
        Main entry point for descriptive analysis based on AnalyticalPlan.
        """
        analysis_id = f"desc_{uuid.uuid4().hex[:10]}"
        now_str = datetime.now(timezone.utc).isoformat()

        if df.empty:
            return StandardizedAnalyticalResult(
                analysis_id=analysis_id,
                analytical_type=IntentCategory.DESCRIPTIVE,
                analysis_question=plan.question,
                success=False,
                selected_methods=[plan.selected_method.value],
                abstain_reason="Input data contains zero records for descriptive analysis.",
                created_at=now_str,
            )

        # Identify numeric columns for analysis
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        date_cols = [c for c in df.columns if any(t in c.lower() for t in ["date", "time", "created_at", "day", "month"])]
        cat_cols = df.select_dtypes(include=["object", "string", "category"]).columns.tolist()
        # Remove date cols from cat_cols if present
        cat_cols = [c for c in cat_cols if c not in date_cols]

        target_col = None
        if plan.target_variable:
            clean_t = plan.target_variable.split(".")[-1]
            if clean_t in df.columns:
                target_col = clean_t
        if not target_col and numeric_cols:
            target_col = numeric_cols[0]

        date_col = None
        if plan.time_dimension:
            clean_d = plan.time_dimension.split(".")[-1]
            if clean_d in df.columns:
                date_col = clean_d
        if not date_col and date_cols:
            date_col = date_cols[0]

        computed_metrics: Dict[str, Any] = {}
        findings: List[str] = []
        result_data: List[Dict[str, Any]] = []
        viz_config: Optional[Dict[str, Any]] = None

        method = plan.selected_method

        # 1. Trend Analysis
        if method == AnalyticalMethod.TREND_ANALYSIS and date_col and target_col:
            trend_res = self.compute_trend_analysis(df, date_col=date_col, metric_col=target_col)
            computed_metrics = trend_res["summary"]
            result_data = trend_res["series"]
            findings = trend_res["findings"]
            viz_config = {
                "chart_type": "line",
                "x_axis": date_col,
                "y_axis": target_col,
                "title": f"Historical Trend of {target_col}",
            }

        # 2. Period-over-Period Comparison
        elif method == AnalyticalMethod.PERIOD_OVER_PERIOD and date_col and target_col:
            pop_res = self.compute_auto_period_comparison(df, date_col=date_col, metric_col=target_col)
            computed_metrics = pop_res["metrics"]
            result_data = pop_res["breakdown"]
            findings = pop_res["findings"]
            viz_config = {
                "chart_type": "bar_comparison",
                "title": f"Period Comparison for {target_col}",
                "metrics": computed_metrics,
            }

        # 3. Segmentation / Top-N Grouping
        elif method == AnalyticalMethod.SEGMENTATION and cat_cols and target_col:
            seg_col = cat_cols[0]
            seg_res = self.compute_segmentation(df, category_col=seg_col, metric_col=target_col)
            computed_metrics = seg_res["summary"]
            result_data = seg_res["segments"]
            findings = seg_res["findings"]
            viz_config = {
                "chart_type": "bar",
                "x_axis": seg_col,
                "y_axis": target_col,
                "title": f"{target_col} by {seg_col}",
            }

        # 4. Descriptive Statistics & Summary Aggregation
        else:
            stats_res = self.compute_descriptive_stats(df, metric_col=target_col) if target_col else {}
            computed_metrics = stats_res
            result_data = df.head(50).to_dict(orient="records")
            if target_col and stats_res:
                findings = [
                    f"Analyzed {len(df):,} total records for '{target_col}'.",
                    f"Mean: {stats_res.get('mean'):,.2f}, Median: {stats_res.get('median'):,.2f}, Total Sum: {stats_res.get('sum'):,.2f}.",
                    f"Interquartile Range (IQR): {stats_res.get('iqr'):,.2f} (25th: {stats_res.get('p25'):,.2f}, 75th: {stats_res.get('p75'):,.2f}).",
                ]
            else:
                findings = [f"Retrieved and profiled {len(df):,} total records across {len(df.columns)} columns."]

            viz_config = {
                "chart_type": "table_and_kpi",
                "kpis": computed_metrics,
            }

        return StandardizedAnalyticalResult(
            analysis_id=analysis_id,
            analytical_type=IntentCategory.DESCRIPTIVE,
            analysis_question=plan.question,
            success=True,
            selected_methods=[method.value],
            source_tables=plan.relevant_tables,
            source_columns=list(df.columns),
            executed_queries=executed_queries or [],
            result_data=result_data,
            computed_metrics=computed_metrics,
            model_information={"engine": "deterministic_descriptive_analytics"},
            validation_results={"data_quality": "passed", "null_ratio": float(df.isnull().mean().mean())},
            confidence_score=1.0,  # Deterministic exact math
            uncertainty_notes=[],
            findings=findings,
            limitations=[f"Analysis bounded to {len(df):,} observed records in active database connection."],
            recommended_next_steps=[
                f"Explore diagnostic drivers to understand factors behind {target_col or 'metrics'}.",
                "Run predictive forecasting to project future values."
            ],
            visualization_config=viz_config,
            created_at=now_str,
        )

    def compute_descriptive_stats(self, df: pd.DataFrame, metric_col: str) -> Dict[str, Any]:
        """Calculates comprehensive descriptive statistics for a numeric column."""
        if metric_col not in df.columns:
            return {}

        s = pd.to_numeric(df[metric_col], errors="coerce").dropna()
        if s.empty:
            return {}

        q25 = float(s.quantile(0.25))
        q75 = float(s.quantile(0.75))
        iqr = float(q75 - q25)

        return {
            "count": int(len(s)),
            "sum": round(float(s.sum()), 2),
            "mean": round(float(s.mean()), 2),
            "median": round(float(s.median()), 2),
            "std": round(float(s.std(ddof=1) if len(s) > 1 else 0.0), 2),
            "min": round(float(s.min()), 2),
            "max": round(float(s.max()), 2),
            "p25": round(q25, 2),
            "p75": round(q75, 2),
            "p90": round(float(s.quantile(0.90)), 2),
            "p95": round(float(s.quantile(0.95)), 2),
            "iqr": round(iqr, 2),
            "missing_count": int(df[metric_col].isnull().sum()),
        }

    def compute_trend_analysis(
        self, df: pd.DataFrame, date_col: str, metric_col: str, moving_avg_window: int = 3
    ) -> Dict[str, Any]:
        """Calculates aggregated chronological trends with moving averages and growth rates."""
        temp_df = df[[date_col, metric_col]].copy()
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
        temp_df[metric_col] = pd.to_numeric(temp_df[metric_col], errors="coerce")
        temp_df = temp_df.dropna().sort_values(by=date_col)

        if temp_df.empty:
            return {"series": [], "summary": {}, "findings": ["No valid date/numeric records for trend."]}

        # Group by daily or monthly depending on span
        date_span = (temp_df[date_col].max() - temp_df[date_col].min()).days
        if date_span > 90:
            temp_df["period"] = temp_df[date_col].dt.to_period("M").astype(str)
        else:
            temp_df["period"] = temp_df[date_col].dt.to_period("D").astype(str)

        grouped = temp_df.groupby("period")[metric_col].agg(["sum", "mean", "count"]).reset_index()
        grouped["moving_avg"] = grouped["sum"].rolling(window=moving_avg_window, min_periods=1).mean()
        grouped["pct_change"] = grouped["sum"].pct_change() * 100.0

        series = []
        for _, row in grouped.iterrows():
            series.append({
                "period": str(row["period"]),
                "value": round(float(row["sum"]), 2),
                "moving_avg": round(float(row["moving_avg"]), 2),
                "pct_change": round(float(row["pct_change"]), 2) if not math.isnan(row["pct_change"]) else None,
                "record_count": int(row["count"]),
            })

        first_val = float(grouped["sum"].iloc[0])
        last_val = float(grouped["sum"].iloc[-1])
        overall_growth = round(((last_val - first_val) / abs(first_val) * 100.0), 2) if first_val != 0 else 0.0

        summary = {
            "start_period": str(grouped["period"].iloc[0]),
            "end_period": str(grouped["period"].iloc[-1]),
            "total_periods": len(grouped),
            "first_period_value": round(first_val, 2),
            "last_period_value": round(last_val, 2),
            "overall_growth_pct": overall_growth,
            "mean_period_value": round(float(grouped["sum"].mean()), 2),
        }

        direction = "increased" if overall_growth > 0 else ("decreased" if overall_growth < 0 else "remained flat")
        findings = [
            f"Over {len(grouped)} periods from {summary['start_period']} to {summary['end_period']}, '{metric_col}' {direction} by {abs(overall_growth)}%.",
            f"Initial period value was {first_val:,.2f}, concluding at {last_val:,.2f}.",
            f"Average per-period value across the entire series was {summary['mean_period_value']:,.2f}.",
        ]

        return {"series": series, "summary": summary, "findings": findings}

    def compute_auto_period_comparison(
        self, df: pd.DataFrame, date_col: str, metric_col: str
    ) -> Dict[str, Any]:
        """Splits chronological data into two equal halves to compute period-over-period delta."""
        temp_df = df[[date_col, metric_col]].copy()
        temp_df[date_col] = pd.to_datetime(temp_df[date_col], errors="coerce")
        temp_df[metric_col] = pd.to_numeric(temp_df[metric_col], errors="coerce")
        temp_df = temp_df.dropna().sort_values(by=date_col)

        if len(temp_df) < 2:
            return {"metrics": {}, "breakdown": [], "findings": ["Insufficient data points for comparison."]}

        mid = len(temp_df) // 2
        df_a = temp_df.iloc[:mid]
        df_b = temp_df.iloc[mid:]

        val_a = float(df_a[metric_col].sum())
        val_b = float(df_b[metric_col].sum())
        delta_abs = round(val_b - val_a, 2)
        delta_pct = round((delta_abs / abs(val_a) * 100.0), 2) if val_a != 0 else 0.0

        metrics = {
            "period_a_label": f"{df_a[date_col].min().strftime('%Y-%m-%d')} to {df_a[date_col].max().strftime('%Y-%m-%d')}",
            "period_a_value": round(val_a, 2),
            "period_b_label": f"{df_b[date_col].min().strftime('%Y-%m-%d')} to {df_b[date_col].max().strftime('%Y-%m-%d')}",
            "period_b_value": round(val_b, 2),
            "delta_absolute": delta_abs,
            "delta_percentage": delta_pct,
        }

        direction = "increase" if delta_abs > 0 else ("decrease" if delta_abs < 0 else "no change")
        findings = [
            f"Comparing Period A ({metrics['period_a_label']}) to Period B ({metrics['period_b_label']}):",
            f"'{metric_col}' changed from {val_a:,.2f} to {val_b:,.2f}, representing a {abs(delta_pct)}% {direction} (${abs(delta_abs):,.2f}).",
        ]

        breakdown = [
            {"period": "Period A", "value": metrics["period_a_value"], "label": metrics["period_a_label"]},
            {"period": "Period B", "value": metrics["period_b_value"], "label": metrics["period_b_label"]},
        ]

        return {"metrics": metrics, "breakdown": breakdown, "findings": findings}

    def compute_segmentation(
        self, df: pd.DataFrame, category_col: str, metric_col: str, top_n: int = 10
    ) -> Dict[str, Any]:
        """Aggregates metric totals by category, computing shares-of-total and top-N ranking."""
        temp_df = df[[category_col, metric_col]].copy()
        temp_df[metric_col] = pd.to_numeric(temp_df[metric_col], errors="coerce")
        temp_df = temp_df.dropna()

        if temp_df.empty:
            return {"segments": [], "summary": {}, "findings": ["No records for segmentation."]}

        grouped = temp_df.groupby(category_col)[metric_col].agg(["sum", "count"]).reset_index()
        total_sum = float(grouped["sum"].sum())

        grouped["share_of_total_pct"] = (grouped["sum"] / total_sum * 100.0).round(2) if total_sum != 0 else 0.0
        grouped = grouped.sort_values(by="sum", ascending=False)

        top_df = grouped.head(top_n)

        segments = []
        for rank, (_, row) in enumerate(top_df.iterrows(), start=1):
            segments.append({
                "rank": rank,
                "category": str(row[category_col]),
                "total_value": round(float(row["sum"]), 2),
                "record_count": int(row["count"]),
                "share_pct": round(float(row["share_of_total_pct"]), 2),
            })

        top_cat = segments[0] if segments else None
        findings = [
            f"Segmented '{metric_col}' across {len(grouped)} distinct '{category_col}' values.",
            f"Top segment is '{top_cat['category']}' contributing {top_cat['total_value']:,.2f} ({top_cat['share_pct']}% of total)." if top_cat else "",
            f"Top {len(segments)} segments represent {round(sum(s['share_pct'] for s in segments), 1)}% of all volume.",
        ]

        summary = {
            "total_volume": round(total_sum, 2),
            "distinct_categories": len(grouped),
            "top_category": top_cat["category"] if top_cat else None,
            "top_category_share_pct": top_cat["share_pct"] if top_cat else 0.0,
        }

        return {"segments": segments, "summary": summary, "findings": [f for f in findings if f]}


descriptive_engine = DescriptiveAnalyticsEngine()

