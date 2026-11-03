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
    Seamlessly executes Descriptive, Diagnostic, Predictive, Prescriptive, and Composite workflows
    with database-isolated conversational follow-up awareness across any database domain.
    """

    def __init__(self):
        # Database-isolated conversational session context: (session_id, db_fingerprint) -> last_result
        self._session_cache: Dict[Tuple[str, str], StandardizedAnalyticalResult] = {}
        # Tracks active database fingerprint per session to detect database switching
        self._active_session_db: Dict[str, str] = {}
        # Database-isolated analytical result cache: (db_fingerprint, normalized_question) -> result
        self._result_cache: Dict[Tuple[str, str], StandardizedAnalyticalResult] = {}

    def analyze(
        self,
        question: str,
        session_id: Optional[str] = None,
        catalog: Optional[DatabaseCatalog] = None,
        fingerprint: Optional[str] = None,
    ) -> StandardizedAnalyticalResult:
        """
        Executes end-to-end analytical intelligence workflow for a natural-language question.
        Enforces strict database fingerprint isolation on all conversational context and cached results.
        """
        cat = catalog or schema_service.get_cached_catalog()
        fp = (
            fingerprint
            or (getattr(cat, "source_fingerprint", None) or getattr(cat, "fingerprint", None) if cat else "default_fp")
            or "default_fp"
        )

        # Step 1: Database-Aware Conversational Context Lookup
        prior_context = None
        if session_id:
            prev_db_fp = self._active_session_db.get(session_id)
            if prev_db_fp and prev_db_fp != fp:
                logger.info(
                    f"Active database switched for session '{session_id}' ({prev_db_fp} -> {fp}). "
                    "Invalidating previous cross-database conversational context."
                )
                self._session_cache.pop((session_id, prev_db_fp), None)

            self._active_session_db[session_id] = fp
            # Context lookup is strictly isolated to (session_id, active_db_fingerprint)
            prior_context = self._session_cache.get((session_id, fp))

        norm_q = " ".join(question.lower().split())

        # Step 2: Intent & Complexity Classification (with composite multi-intent detection)
        intent_res = intent_classifier.classify(question)
        logger.info(
            f"Classified question: '{question[:60]}...' -> Intent: {intent_res.primary_intent.value}, "
            f"Complexity: {intent_res.complexity.value}, Composite: {intent_res.is_composite}, Confidence: {intent_res.confidence_score}"
        )

        # If question requires genuine ambiguity clarification, return early
        if intent_res.requires_clarification and intent_res.suggested_clarification:
            return StandardizedAnalyticalResult(
                analysis_id=f"clarify_{int(datetime.now(timezone.utc).timestamp())}",
                analytical_type=intent_res.primary_intent,
                analysis_question=question,
                success=False,
                confidence_score=intent_res.confidence_score,
                abstain_reason=intent_res.suggested_clarification,
                findings=[intent_res.suggested_clarification],
                limitations=["Ambiguous inquiry requiring user clarification."],
            )

        # Step 3: Schema-Grounded Analytical Planning
        plan = analytical_planner.create_plan(
            question=question,
            catalog=cat,
            fingerprint=fp,
            intent_override=intent_res.primary_intent,
        )

        # Ground with prior turn if conversational follow-up within SAME database
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

        # Step 5: Route to Specialized Generic Analytical Engine (Sequential Multi-Stage Pipeline)
        if intent_res.is_composite and len(intent_res.composite_intents) >= 2:
            stages = intent_res.composite_intents
            logger.info(f"Executing composite multi-stage analytical pipeline: {[s.value for s in stages]}")

            stage_results: Dict[IntentCategory, StandardizedAnalyticalResult] = {}
            stage_statuses: Dict[str, str] = {}
            executed_stage_methods: List[str] = []
            combined_findings: List[str] = []
            combined_limitations: List[str] = []
            combined_uncertainties: List[str] = []
            combined_recommendations: List[str] = []
            combined_metrics: Dict[str, Any] = {}
            primary_result_data: List[Dict[str, Any]] = []
            primary_viz_config: Optional[Dict[str, Any]] = None

            for stage_intent in stages:
                # Configure stage-specific plan
                mapped_methods = intent_classifier._map_methods(stage_intent, plan.complexity, question.lower())
                stage_method = mapped_methods[0] if mapped_methods else AnalyticalMethod.SQL_QUERY_ONLY
                stage_plan = plan.model_copy(update={
                    "intent": stage_intent,
                    "selected_method": stage_method,
                })
                r_stage = self._dispatch_single_engine(stage_intent, df, stage_plan, executed_queries)
                stage_results[stage_intent] = r_stage

                if r_stage.success:
                    stage_statuses[stage_intent.value] = "COMPLETED"
                    executed_stage_methods.extend(r_stage.selected_methods)
                    combined_findings.extend(r_stage.findings)
                    combined_limitations.extend(r_stage.limitations)
                    combined_uncertainties.extend(r_stage.uncertainty_notes)
                    combined_recommendations.extend(r_stage.recommended_next_steps)
                    for k, v in r_stage.computed_metrics.items():
                        combined_metrics[f"{stage_intent.value}_{k}"] = v
                        combined_metrics[k] = v

                    if r_stage.result_data and not primary_result_data:
                        primary_result_data = r_stage.result_data
                    if r_stage.visualization_config and not primary_viz_config:
                        primary_viz_config = r_stage.visualization_config
                else:
                    stage_statuses[stage_intent.value] = "ABSTAINED"
                    combined_findings.append(f"Stage {stage_intent.value} abstained: {r_stage.abstain_reason}")
                    combined_limitations.append(f"Stage {stage_intent.value} could not execute: {r_stage.abstain_reason}")

            overall_success = any(res.success for res in stage_results.values())
            all_stages_completed = all(status == "COMPLETED" for status in stage_statuses.values())

            completed_stages = [s for s in stages if stage_statuses.get(s.value) == "COMPLETED"]
            primary_stage = completed_stages[-1] if completed_stages else stages[0]

            model_info: Dict[str, Any] = {
                "composite_stages": [s.value for s in stages],
                "composite_intents": [s.value for s in stages],
                "stage_statuses": stage_statuses,
                "stage_count": len(stages),
                "completed_stage_count": len(completed_stages),
            }

            if IntentCategory.PREDICTIVE in stage_results and stage_results[IntentCategory.PREDICTIVE].success:
                r_pred = stage_results[IntentCategory.PREDICTIVE]
                if r_pred.result_data:
                    model_info["forecast_preview"] = r_pred.result_data[:3]
                if "selected_model" in r_pred.model_information:
                    model_info["selected_model"] = r_pred.model_information["selected_model"]

            if IntentCategory.PRESCRIPTIVE in stage_results and stage_results[IntentCategory.PRESCRIPTIVE].success:
                r_presc = stage_results[IntentCategory.PRESCRIPTIVE]
                model_info["prescriptive_summary"] = r_presc.computed_metrics
                if r_presc.visualization_config:
                    primary_viz_config = r_presc.visualization_config

            result = StandardizedAnalyticalResult(
                analysis_id=plan.plan_id,
                analytical_type=primary_stage,
                analysis_question=question,
                success=overall_success,
                selected_methods=list(dict.fromkeys(executed_stage_methods)),
                source_tables=plan.relevant_tables,
                source_columns=list(df.columns) if not df.empty else [],
                executed_queries=executed_queries or [],
                result_data=primary_result_data,
                computed_metrics=combined_metrics,
                model_information=model_info,
                validation_results={"multi_stage_pipeline_executed": True, "all_stages_completed": all_stages_completed},
                confidence_score=0.90 if all_stages_completed else 0.75,
                uncertainty_notes=list(dict.fromkeys(combined_uncertainties)),
                findings=combined_findings,
                limitations=list(dict.fromkeys(combined_limitations)),
                recommended_next_steps=list(dict.fromkeys(combined_recommendations)),
                visualization_config=primary_viz_config,
            )
        else:
            result = self._dispatch_single_engine(plan.intent, df, plan, executed_queries)

        # Step 6: Result Faithfulness Validation
        narrative_text = " ".join(result.findings)
        faith_report = faithfulness_validator.validate_narrative(
            narrative=narrative_text,
            ground_truth_metrics=result.computed_metrics,
            ground_truth_data=result.result_data,
        )
        result.faithfulness = faith_report
        result.faithfulness_report = faith_report

        # Discount confidence if faithfulness discrepancies found
        if not faith_report.is_faithful:
            result.confidence_score = max(0.40, result.confidence_score - faith_report.confidence_discount)
            result.limitations.extend(faith_report.discrepancies)

        # Step 7: Update Database-Isolated Session Cache and Result Cache
        if session_id and result.success:
            self._session_cache[(session_id, fp)] = result

        if result.success and not prior_context:
            self._result_cache[(fp, norm_q)] = result

        return result

    def _dispatch_single_engine(
        self,
        intent: IntentCategory,
        df: pd.DataFrame,
        plan: AnalyticalPlan,
        executed_queries: Optional[List[str]],
    ) -> StandardizedAnalyticalResult:
        """Routes execution to specialized analytical engine."""
        if intent in [IntentCategory.DESCRIPTIVE, IntentCategory.SQL_LOOKUP]:
            return descriptive_engine.run_descriptive_analysis(df, plan, executed_queries=executed_queries)
        elif intent == IntentCategory.DIAGNOSTIC:
            return diagnostic_engine.run_diagnostic_analysis(df, plan, executed_queries=executed_queries)
        elif intent == IntentCategory.PREDICTIVE:
            return predictive_engine.run_predictive_analysis(df, plan, executed_queries=executed_queries)
        elif intent == IntentCategory.PRESCRIPTIVE:
            return prescriptive_engine.run_prescriptive_analysis(df, plan, executed_queries=executed_queries)
        else:
            return descriptive_engine.run_descriptive_analysis(df, plan, executed_queries=executed_queries)

    def clear_session(self, session_id: str) -> None:
        """Clears cached conversational context for a session across all databases."""
        keys_to_del = [k for k in self._session_cache if k[0] == session_id]
        for k in keys_to_del:
            self._session_cache.pop(k, None)
        self._active_session_db.pop(session_id, None)

    def clear_database_cache(self, fingerprint: str) -> None:
        """Clears all session and result caches associated with a database fingerprint."""
        s_keys = [k for k in self._session_cache if k[1] == fingerprint]
        for k in s_keys:
            self._session_cache.pop(k, None)
        r_keys = [k for k in self._result_cache if k[0] == fingerprint]
        for k in r_keys:
            self._result_cache.pop(k, None)


analytical_orchestrator = AnalyticalOrchestrator()

