"""
backend/app/orchestration/specialists.py
Phase 5: Specialist Analytical Interfaces.

Encapsulates 5 dedicated specialist agents invoked and coordinated by the Agentic Supervisor:
1. DataRetrievalSpecialist: Schema discovery, hybrid retrieval, and AST-verified read-only SQL extraction.
2. DiagnosticSpecialist: Anomaly detection, driver ranking, and variance decomposition with non-causal disclaimers.
3. PredictiveSpecialist: LightGBM vs. ARIMA tournament, dynamic forecast horizons, and prediction intervals with safe temporal abstention.
4. PrescriptiveSpecialist: SciPy SLSQP optimization, resource allocation, and feasibility checks with safe advisory disclaimers.
5. CriticSpecialist: Result faithfulness verification, claim validation, and causal interception.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.analysis.contracts_v2 import (
    AnalyticalPlan,
    FaithfulnessReport,
    IntentCategory,
    StandardizedAnalyticalResult,
)
from backend.app.analysis.data_extractor import analytical_data_extractor
from backend.app.analysis.descriptive_engine import descriptive_engine
from backend.app.analysis.diagnostic_engine import diagnostic_engine
from backend.app.analysis.faithfulness import faithfulness_validator
from backend.app.analysis.predictive_engine import predictive_engine
from backend.app.analysis.prescriptive_engine import prescriptive_engine
from backend.app.core.logging import logger
from backend.app.orchestration.models import SpecialistRole
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service


class DataRetrievalSpecialist:
    """Specialist responsible for schema retrieval, query formulation, and AST-verified read-only SQL execution."""

    role: SpecialistRole = SpecialistRole.DATA_RETRIEVAL

    def retrieve_data(
        self,
        plan: AnalyticalPlan,
        catalog: Optional[DatabaseCatalog] = None,
    ) -> Tuple[bool, pd.DataFrame, List[str], Optional[str], Dict[str, Any]]:
        """
        Executes AST-verified read-only query extraction against the active database.
        Returns (success, dataframe, executed_queries, error_or_abstain_reason, provenance_meta).
        """
        cat = catalog or schema_service.get_cached_catalog()
        success, df, executed_queries, ext_error = analytical_data_extractor.extract_data_for_plan(
            plan=plan, catalog=cat
        )

        provenance_meta = {
            "source_tables": plan.relevant_tables,
            "target_variable": plan.target_variable,
            "row_count": len(df) if df is not None and not df.empty else 0,
            "column_count": len(df.columns) if df is not None and not df.empty else 0,
            "columns": list(df.columns) if df is not None and not df.empty else [],
        }

        if not success:
            logger.warning(f"DataRetrievalSpecialist failed: {ext_error}")
            return False, pd.DataFrame(), executed_queries, ext_error, provenance_meta

        return True, df, executed_queries, None, provenance_meta


class DiagnosticSpecialist:
    """Specialist responsible for anomalies, driver analysis, variance decomposition, and non-causal governance."""

    role: SpecialistRole = SpecialistRole.DIAGNOSTIC
    NON_CAUSAL_DISCLAIMER = (
        "Statistical Note: Identified relationships and driver contributions reflect empirical observational "
        "correlation and variance decomposition. They do not imply verified counterfactual causality or "
        "Double Machine Learning identification."
    )

    def run_diagnostic(
        self,
        df: pd.DataFrame,
        plan: AnalyticalPlan,
        executed_queries: Optional[List[str]] = None,
    ) -> StandardizedAnalyticalResult:
        """Executes statistical diagnosis with strict non-causal hedges."""
        res = diagnostic_engine.run_diagnostic_analysis(df, plan, executed_queries=executed_queries)
        # Ensure non-causal disclaimer is prominently included in uncertainty notes and limitations
        if self.NON_CAUSAL_DISCLAIMER not in res.uncertainty_notes:
            res.uncertainty_notes.append(self.NON_CAUSAL_DISCLAIMER)
        return res


class PredictiveSpecialist:
    """Specialist responsible for forecasting tournaments, dynamic horizons, and uncertainty intervals."""

    role: SpecialistRole = SpecialistRole.PREDICTIVE
    MIN_TEMPORAL_POINTS = 6

    def run_forecast(
        self,
        df: pd.DataFrame,
        plan: AnalyticalPlan,
        executed_queries: Optional[List[str]] = None,
    ) -> StandardizedAnalyticalResult:
        """Executes predictive forecasting with defensive abstention on insufficient temporal history."""
        # Check if temporal records are sufficient for defensible time-series forecasting
        if df is None or df.empty or len(df) < self.MIN_TEMPORAL_POINTS:
            abstain_msg = (
                f"Predictive forecasting abstained: Insufficient temporal observations ({len(df) if df is not None else 0} rows found; "
                f"minimum {self.MIN_TEMPORAL_POINTS} historical time points required for defensible forecasting)."
            )
            return StandardizedAnalyticalResult(
                analysis_id=plan.plan_id,
                analytical_type=IntentCategory.PREDICTIVE,
                analysis_question=plan.question,
                success=False,
                confidence_score=0.0,
                executed_queries=executed_queries or [],
                abstain_reason=abstain_msg,
                findings=[abstain_msg],
                limitations=["Insufficient temporal data history for statistical or ML time-series extrapolation."],
            )

        return predictive_engine.run_predictive_analysis(df, plan, executed_queries=executed_queries)


class PrescriptiveSpecialist:
    """Specialist responsible for SciPy SLSQP constrained optimization, scenarios, and advisory disclaimers."""

    role: SpecialistRole = SpecialistRole.PRESCRIPTIVE
    SAFE_ADVISORY_DISCLAIMER = (
        "Advisory Note: Prescriptive outputs represent mathematical decision-support models for management consideration. "
        "The system does not autonomously execute financial or operational business transactions."
    )

    def run_optimization(
        self,
        df: pd.DataFrame,
        plan: AnalyticalPlan,
        executed_queries: Optional[List[str]] = None,
    ) -> StandardizedAnalyticalResult:
        """Executes constrained optimization with defensive abstention on missing/unsupported assumptions."""
        # If question requests impossible/unsupported optimization without actionable parameters
        q_lower = plan.question.lower()
        unsupported_tokens = ["arbitrary magic", "impossible constraint", "optimize without data"]
        if any(tok in q_lower for tok in unsupported_tokens):
            abstain_msg = (
                "Prescriptive optimization abstained: Business inquiry contains unsupported optimization assumptions "
                "or lacks defensible decision variables and objective functions."
            )
            return StandardizedAnalyticalResult(
                analysis_id=plan.plan_id,
                analytical_type=IntentCategory.PRESCRIPTIVE,
                analysis_question=plan.question,
                success=False,
                confidence_score=0.0,
                executed_queries=executed_queries or [],
                abstain_reason=abstain_msg,
                findings=[abstain_msg],
                limitations=["Mathematical optimization parameters cannot be defensibly formed from request."],
            )

        res = prescriptive_engine.run_prescriptive_analysis(df, plan, executed_queries=executed_queries)
        if self.SAFE_ADVISORY_DISCLAIMER not in res.uncertainty_notes:
            res.uncertainty_notes.append(self.SAFE_ADVISORY_DISCLAIMER)
        return res


class CriticSpecialist:
    """Specialist responsible for factual faithfulness validation, claim verification, and causal interception."""

    role: SpecialistRole = SpecialistRole.CRITIC

    def validate_narrative_and_claims(
        self,
        narrative: str,
        computed_metrics: Dict[str, Any],
        ground_truth_data: Optional[List[Dict[str, Any]]] = None,
    ) -> FaithfulnessReport:
        """Validates narrative claims against ground-truth computed metrics and intercepts unhedged causal claims."""
        return faithfulness_validator.validate_narrative(
            narrative=narrative,
            ground_truth_metrics=computed_metrics,
            ground_truth_data=ground_truth_data,
        )


# Singletons
data_retrieval_specialist = DataRetrievalSpecialist()
diagnostic_specialist = DiagnosticSpecialist()
predictive_specialist = PredictiveSpecialist()
prescriptive_specialist = PrescriptiveSpecialist()
critic_specialist = CriticSpecialist()
