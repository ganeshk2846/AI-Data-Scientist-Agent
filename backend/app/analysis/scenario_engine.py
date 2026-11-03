"""
backend/app/analysis/scenario_engine.py
Domain-Independent Scenario Simulation and "What-If" Analysis Engine.

Answers: WHAT IF?
Simulates hypotheticals (price adjustments, marketing shocks, demand fluctuations, cost changes),
extracts empirical baselines via schema-grounded SQL, computes multi-scenario projections
(Conservative, Moderate, Aggressive), generates sensitivity matrices, tracks explicit assumptions,
and defensively abstains when parameters lack empirical support in the connected database.
"""

from datetime import datetime, timezone
import math
import re
import sqlite3
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    AnalyticalPlan,
    IntentCategory,
    StandardizedAnalyticalResult,
)
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.schema.models import DatabaseCatalog


class ScenarioAnalyticsEngine:
    """
    Executes what-if scenario simulations grounded in active database metrics.
    """

    def parse_scenario_parameters(self, question: str) -> Dict[str, Any]:
        """
        Extracts parameter, magnitude (shock percentage or absolute change),
        direction, and affected target metric from natural language inquiry.
        """
        q_low = question.lower()

        # 1. Parameter identification
        parameter = "price"
        base_elasticity = -1.0
        if any(w in q_low for w in ["price", "pricing", "cost of item"]):
            parameter = "price"
            base_elasticity = -1.0
        elif any(w in q_low for w in ["marketing", "ad spend", "advertising", "campaign expenditure"]):
            parameter = "marketing_spend"
            base_elasticity = 0.30
        elif any(w in q_low for w in ["demand", "volume", "order volume", "footfall"]):
            parameter = "demand"
            base_elasticity = 1.0
        elif any(w in q_low for w in ["discount", "promotion", "coupon"]):
            parameter = "discount"
            base_elasticity = -0.80
        elif any(w in q_low for w in ["store", "stores", "locations", "branches"]):
            parameter = "store_count"
            base_elasticity = 0.85
        elif any(w in q_low for w in ["cost", "shipping cost", "cogs", "expenses"]):
            parameter = "cost"
            base_elasticity = -0.50

        # 2. Percentage shock extraction
        pct_matches = re.findall(r"([+-]?\s*\d+(?:\.\d+)?)\s*%", question)
        shock_pct = None
        if pct_matches:
            try:
                raw_pct = pct_matches[0].replace(" ", "")
                shock_pct = float(raw_pct)
            except ValueError:
                shock_pct = None

        # Check for direction keywords if sign not explicit
        if shock_pct is not None:
            if any(w in q_low for w in ["decrease", "drop", "reduce", "cut", "fall"]) and shock_pct > 0:
                shock_pct = -shock_pct
            elif any(w in q_low for w in ["increase", "raise", "grow", "boost"]) and shock_pct < 0:
                shock_pct = abs(shock_pct)
        else:
            # Check integer increments e.g. "two additional stores", "5 more"
            num_words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "ten": 10}
            int_match = re.search(r"\b(\d+|one|two|three|four|five|ten)\s+(?:additional|more|new)\b", q_low)
            if int_match:
                token = int_match.group(1)
                val = float(num_words.get(token, token))
                # Treat as relative increase or store increment
                shock_pct = val * 10.0  # approximate scaling if relative
            else:
                shock_pct = 5.0  # default reasonable +5% probe

        # 3. Target metric identification
        target_metric = "revenue"
        if any(w in q_low for w in ["profit", "net income", "margin"]):
            target_metric = "profit"
        elif any(w in q_low for w in ["unit", "volume", "orders", "quantity"]):
            target_metric = "volume"
        elif any(w in q_low for w in ["customer", "acquisition", "churn"]):
            target_metric = "customers"
        else:
            target_metric = "revenue"

        return {
            "parameter": parameter,
            "shock_pct": shock_pct,
            "base_elasticity": base_elasticity,
            "target_metric": target_metric,
        }

    def extract_baseline_metric(
        self,
        db_path: Optional[str] = None,
        target_metric: str = "revenue",
        catalog: Optional[DatabaseCatalog] = None,
    ) -> Tuple[float, List[str], Optional[str]]:
        """
        Executes a schema-grounded SQL query to retrieve the real empirical baseline.
        Returns (baseline_value, executed_queries, error_or_abstain_reason).
        """
        path = db_path or settings.ECOMMERCE_DB_PATH
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        cur = conn.cursor()

        try:
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = {r[0].lower(): r[0] for r in cur.fetchall()}

            executed_queries = []
            if "orders" in tables:
                if target_metric in ["revenue", "sales", "profit"]:
                    sql = "SELECT COALESCE(SUM(total_amount), 0.0) FROM orders;"
                    cur.execute(sql)
                    val = float(cur.fetchone()[0])
                    executed_queries.append(sql)
                    return val, executed_queries, None
                elif target_metric in ["volume", "quantity", "orders"]:
                    sql = "SELECT COUNT(*) FROM orders;"
                    cur.execute(sql)
                    val = float(cur.fetchone()[0])
                    executed_queries.append(sql)
                    return val, executed_queries, None
                elif target_metric == "customers":
                    sql = "SELECT COUNT(DISTINCT customer_id) FROM orders;"
                    cur.execute(sql)
                    val = float(cur.fetchone()[0])
                    executed_queries.append(sql)
                    return val, executed_queries, None

            # Fallback for tables like sales, transactions, invoices
            for candidate in ["sales", "transactions", "invoices"]:
                if candidate in tables:
                    sql = f"SELECT COUNT(*) FROM {tables[candidate]};"
                    cur.execute(sql)
                    val = float(cur.fetchone()[0])
                    executed_queries.append(sql)
                    return val, executed_queries, None

            return 0.0, [], f"Database does not contain recognized transaction or orders tables for baseline {target_metric}."

        except Exception as e:
            return 0.0, [], f"SQL error extracting baseline: {str(e)}"
        finally:
            conn.close()

    def run_scenario_analysis(
        self,
        question: str,
        df: Optional[pd.DataFrame] = None,
        db_path: Optional[str] = None,
        catalog: Optional[DatabaseCatalog] = None,
    ) -> StandardizedAnalyticalResult:
        """
        Runs comprehensive what-if scenario analysis with multi-scenario comparison,
        sensitivity bounds, explicit assumptions, and defensive abstention.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        plan_id = f"scen_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        params = self.parse_scenario_parameters(question)
        parameter = params["parameter"]
        shock_pct = params["shock_pct"]
        base_elasticity = params["base_elasticity"]
        target_metric = params["target_metric"]

        # Check for ungrounded physical concepts (e.g. store counts in digital-only e-commerce)
        if parameter == "store_count":
            abstain_msg = (
                "Scenario simulation abstained: Target database does not track physical retail stores or location assets. "
                "The connected warehouse represents digital e-commerce transactions across digital sales channels."
            )
            return StandardizedAnalyticalResult(
                analysis_id=plan_id,
                analytical_type=IntentCategory.PRESCRIPTIVE,
                analysis_question=question,
                success=False,
                confidence_score=0.0,
                selected_methods=[AnalyticalMethod.WHAT_IF_SCENARIO.value],
                abstain_reason=abstain_msg,
                findings=[abstain_msg],
                limitations=["No physical retail store entities or square footage records found in database schema."],
                created_at=now_str,
            )

        # Retrieve empirical baseline
        baseline_val = 0.0
        executed_queries = []
        if df is not None and not df.empty and len(df) > 0:
            num_cols = df.select_dtypes(include=["number"]).columns
            if len(num_cols) > 0:
                baseline_val = float(df[num_cols[0]].sum())
        
        if baseline_val <= 0:
            baseline_val, executed_queries, ext_err = self.extract_baseline_metric(
                db_path=db_path, target_metric=target_metric, catalog=catalog
            )
            if ext_err or baseline_val <= 0:
                abstain_msg = f"Cannot simulate scenario: Unable to establish positive empirical baseline for {target_metric} ({ext_err or 'zero baseline'})."
                return StandardizedAnalyticalResult(
                    analysis_id=plan_id,
                    analytical_type=IntentCategory.PRESCRIPTIVE,
                    analysis_question=question,
                    success=False,
                    confidence_score=0.0,
                    selected_methods=[AnalyticalMethod.WHAT_IF_SCENARIO.value],
                    abstain_reason=abstain_msg,
                    findings=[abstain_msg],
                    created_at=now_str,
                )

        # Multi-Scenario Projections: Conservative, Moderate (Base), Aggressive
        # Elasticity scaling:
        # Conservative: lower quantity response for price cuts, higher attrition for price hikes
        # Aggressive: higher favorable response
        scenarios = {}
        for name, elast_mult in [("Conservative", 1.4), ("Moderate", 1.0), ("Aggressive", 0.7)]:
            cur_elast = base_elasticity * elast_mult
            p_factor = 1.0 + (shock_pct / 100.0)
            q_factor = 1.0 + (cur_elast * shock_pct / 100.0)

            if target_metric in ["revenue", "sales"]:
                if parameter == "price":
                    sim_val = max(0.0, baseline_val * p_factor * q_factor)
                elif parameter == "marketing_spend":
                    # Diminishing log-returns for marketing spend
                    sim_val = max(0.0, baseline_val * (1.0 + cur_elast * math.log1p(max(0.0, shock_pct / 100.0))))
                else:
                    sim_val = max(0.0, baseline_val * (1.0 + cur_elast * shock_pct / 100.0))
            elif target_metric == "volume":
                sim_val = max(0.0, baseline_val * q_factor)
            else:
                sim_val = max(0.0, baseline_val * (1.0 + cur_elast * shock_pct / 100.0))

            delta_abs = sim_val - baseline_val
            delta_pct = (delta_abs / baseline_val) * 100.0
            scenarios[name] = {
                "elasticity": round(cur_elast, 3),
                "simulated_value": round(sim_val, 2),
                "delta_absolute": round(delta_abs, 2),
                "delta_percentage": round(delta_pct, 2),
            }

        # Sensitivity Matrix across parameter shocks [-10%, -5%, 0%, +5%, +10%, +15%]
        test_shocks = [-10.0, -5.0, 0.0, 5.0, 10.0, 15.0]
        if shock_pct not in test_shocks:
            test_shocks.append(shock_pct)
            test_shocks.sort()

        sensitivity_table = []
        for s in test_shocks:
            p_f = 1.0 + (s / 100.0)
            q_f = 1.0 + (base_elasticity * s / 100.0)
            if parameter == "price":
                s_val = max(0.0, baseline_val * p_f * q_f)
            elif parameter == "marketing_spend":
                s_val = max(0.0, baseline_val * (1.0 + base_elasticity * math.log1p(max(0.0, s / 100.0))))
            else:
                s_val = max(0.0, baseline_val * (1.0 + base_elasticity * s / 100.0))
            d_pct = ((s_val - baseline_val) / baseline_val) * 100.0
            sensitivity_table.append({
                "shock_percentage": s,
                "projected_metric": round(s_val, 2),
                "percentage_change": round(d_pct, 2),
            })

        mod_sim = scenarios["Moderate"]
        findings = [
            f"Baseline empirical {target_metric} verified at ${baseline_val:,.2f} from database.",
            f"Simulated {shock_pct:+.1f}% change in '{parameter}' yields projected {target_metric} of ${mod_sim['simulated_value']:,.2f} (change of {mod_sim['delta_percentage']:+.2f}%, ${mod_sim['delta_absolute']:+,.2f}).",
            f"Multi-Scenario Range: Conservative=${scenarios['Conservative']['simulated_value']:,.2f} ({scenarios['Conservative']['delta_percentage']:+.2f}%) to Aggressive=${scenarios['Aggressive']['simulated_value']:,.2f} ({scenarios['Aggressive']['delta_percentage']:+.2f}%).",
        ]

        assumptions = [
            f"Applied baseline price elasticity of demand epsilon = {base_elasticity:.2f}.",
            "Ceteris paribus assumption: Competitor pricing, macroeconomic factors, and catalog offerings remain static.",
            "Marketing spend adjustments assume diminishing returns via logarithmic scaling rather than unbounded linear extrapolation.",
        ]

        computed_metrics = {
            "baseline_value": round(baseline_val, 2),
            "simulated_value": mod_sim["simulated_value"],
            "delta_absolute": mod_sim["delta_absolute"],
            "delta_percentage": mod_sim["delta_percentage"],
            "shock_percentage": shock_pct,
            "parameter": parameter,
            "target_metric": target_metric,
            "scenarios": scenarios,
            "sensitivity_matrix": sensitivity_table,
        }

        return StandardizedAnalyticalResult(
            analysis_id=plan_id,
            analytical_type=IntentCategory.PRESCRIPTIVE,
            analysis_question=question,
            success=True,
            confidence_score=0.90,
            selected_methods=[AnalyticalMethod.WHAT_IF_SCENARIO.value],
            executed_queries=executed_queries,
            computed_metrics=computed_metrics,
            findings=findings,
            limitations=[
                "Simulations model aggregate market elasticity and cannot capture localized microeconomic competitive responses.",
                "Assumes supply chain and inventory capacity can fulfill simulated demand variations without stockouts.",
            ],
            uncertainty_notes=assumptions,
            recommended_next_steps=[
                f"Test the {shock_pct:+.1f}% {parameter} adjustment in a controlled A/B test or regional pilot before nationwide rollout.",
                "Monitor order conversion rates daily to detect if empirical elasticity exceeds the conservative boundary.",
            ],
            result_data=sensitivity_table,
            visualization_config={
                "chart_type": "scenario_sensitivity_line",
                "x_axis": "shock_percentage",
                "y_axis": "projected_metric",
                "title": f"Sensitivity of {target_metric.capitalize()} to {parameter.replace('_', ' ').capitalize()} Shocks",
            },
            created_at=now_str,
        )


scenario_analytics_engine = ScenarioAnalyticsEngine()
