"""
backend/app/analysis/orchestrator.py
Unified Domain-Independent Analytical Orchestration Engine for Phase 4.
Orchestrates:
Intent Classification -> Schema-Grounded Planning -> Safe Read-Only Extraction ->
Method Execution (Descriptive, Diagnostic, Predictive, Prescriptive) ->
Result Faithfulness Validation -> Conversational State Memory.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import pandas as pd

from backend.app.analysis.contracts_v2 import (
    AnalyticalPlan,
    IntentCategory,
    StandardizedAnalyticalResult,
)
from backend.app.analysis.data_extractor import analytical_data_extractor
from backend.app.analysis.descriptive_engine import descriptive_engine
from backend.app.analysis.diagnostic_engine import diagnostic_engine
from backend.app.analysis.faithfulness import faithfulness_validator
from backend.app.analysis.intent_classifier import intent_classifier
from backend.app.analysis.planner import analytical_planner
from backend.app.analysis.predictive_engine import predictive_engine
from backend.app.analysis.prescriptive_engine import prescriptive_engine
from backend.app.core.logging import logger
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service


class AnalyticalOrchestrator:
    """
    Unified entry point for AI Data Analyst & Data Scientist intelligence.
    Seamlessly executes Descriptive, Diagnostic, Predictive, and Prescriptive workflows
    with conversational follow-up awareness across any database domain.
    """

    def __init__(self):
        # In-memory conversational state: session_id -> last_result
        self._session_cache: Dict[str, StandardizedAnalyticalResult] = {}

    def analyze(
        self,
        question: str,
        session_id: Optional[str] = None,
        catalog: Optional[DatabaseCatalog] = None,
        fingerprint: Optional[str] = None,
    ) -> StandardizedAnalyticalResult:
        """
        Executes end-to-end analytical intelligence workflow for a natural-language question.
        """
        cat = catalog or schema_service.get_cached_catalog()
        fp = fingerprint or (getattr(cat, "fingerprint", None) if cat else None)

        # Step 1: Conversational context lookup for follow-ups
        prior_context = self._session_cache.get(session_id) if session_id else None

        # Step 2: Intent & Complexity Classification
        intent_res = intent_classifier.classify(question)
        logger.info(
            f"Classified question: '{question[:60]}...' -> Intent: {intent_res.primary_intent.value}, "
            f"Complexity: {intent_res.complexity.value}, Confidence: {intent_res.confidence_score}"
        )

        # If question requires clarification, return early
        if intent_res.requires_clarification and intent_res.suggested_clarification:
            return StandardizedAnalyticalResult(
                analysis_id=f"clarify_{int(datetime.now(timezone.utc).timestamp())}",
                analytical_type=intent_res.primary_intent,
                analysis_question=question,
                success=False,
                confidence_score=intent_res.confidence_score,
                abstain_reason=intent_res.suggested_clarification,
                findings=[intent_res.suggested_clarification],
                limitations=["Ambiguous multi-intent inquiry."],
            )

        # Step 3: Schema-Grounded Analytical Planning
        plan = analytical_planner.create_plan(
            question=question,
            catalog=cat,
            fingerprint=fp,
            intent_override=intent_res.primary_intent,
        )

        # Ground with prior turn if conversational follow-up (e.g., "Why did they decrease?")
        if prior_context and prior_context.success:
            if not plan.target_variable and prior_context.source_columns:
                plan = plan.model_copy(update={"target_variable": prior_context.source_columns[0]})
            if not plan.relevant_tables and prior_context.source_tables:
                plan = plan.model_copy(update={"relevant_tables": prior_context.source_tables})

        if not plan.is_executable:
            return StandardizedAnalyticalResult(
                analysis_id=plan.plan_id,
                analytical_type=plan.intent,
                analysis_question=question,
                success=False,
                confidence_score=0.0,
                abstain_reason=plan.abstain_reason or "Plan deemed non-executable due to schema constraints.",
                findings=[plan.abstain_reason or "Analysis abstained."],
                limitations=["Database schema does not support requested analytical attributes."],
            )

        # Step 4: Analytical Data Extraction (Read-Only AST Guarded)
        success, df, executed_queries, ext_error = analytical_data_extractor.extract_data_for_plan(
            plan=plan, catalog=cat
        )

        if not success or df is None or df.empty:
            # If optimization or scenario query with parameter data, engine can operate parametrically
            if plan.intent == IntentCategory.PRESCRIPTIVE:
                df = pd.DataFrame()
            else:
                return StandardizedAnalyticalResult(
                    analysis_id=plan.plan_id,
                    analytical_type=plan.intent,
                    analysis_question=question,
                    success=False,
                    executed_queries=executed_queries,
                    abstain_reason=ext_error or "Data extraction returned 0 records.",
                    findings=[ext_error or "Data extraction failed."],
                )

        # Step 5: Route to Specialized Generic Analytical Engine
        if plan.intent in [IntentCategory.DESCRIPTIVE, IntentCategory.SQL_LOOKUP]:
            result = descriptive_engine.run_descriptive_analysis(df, plan, executed_queries=executed_queries)
        elif plan.intent == IntentCategory.DIAGNOSTIC:
            result = diagnostic_engine.run_diagnostic_analysis(df, plan, executed_queries=executed_queries)
        elif plan.intent == IntentCategory.PREDICTIVE:
            result = predictive_engine.run_predictive_analysis(df, plan, executed_queries=executed_queries)
        elif plan.intent == IntentCategory.PRESCRIPTIVE:
            result = prescriptive_engine.run_prescriptive_analysis(df, plan, executed_queries=executed_queries)
        else:
            result = descriptive_engine.run_descriptive_analysis(df, plan, executed_queries=executed_queries)

        # Step 6: Result Faithfulness Validation
        narrative_text = " ".join(result.findings)
        faith_report = faithfulness_validator.validate_narrative(
            narrative=narrative_text,
            ground_truth_metrics=result.computed_metrics,
            ground_truth_data=result.result_data,
        )
        result.faithfulness = faith_report

        # Discount confidence if faithfulness discrepancies found
        if not faith_report.is_faithful:
            result.confidence_score = max(0.40, result.confidence_score - faith_report.confidence_discount)
            result.limitations.extend(faith_report.discrepancies)

        # Step 7: Update Session Cache for conversational continuity
        if session_id and result.success:
            self._session_cache[session_id] = result

        return result

    def clear_session(self, session_id: str) -> None:
        """Clears cached conversational context for a session."""
        self._session_cache.pop(session_id, None)


analytical_orchestrator = AnalyticalOrchestrator()

