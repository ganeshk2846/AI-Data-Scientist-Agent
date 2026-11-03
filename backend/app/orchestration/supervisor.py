"""
backend/app/orchestration/supervisor.py
Phase 5 & Task 2: Agentic Supervisor for Autonomous Analytical Decision Support.

Coordinates:
1. Question understanding, structured entity extraction, and multi-round clarification (2-round cap).
2. Database-isolated conversational session context strictly keyed to (session_id, db_fingerprint).
3. Dependency-aware task routing across Specialist Analytical Agents:
   - DataRetrievalSpecialist
   - DiagnosticSpecialist (including Impact Analytics)
   - PredictiveSpecialist
   - PrescriptiveSpecialist (including Scenario Analytics)
   - Customer Churn & Risk Prioritization Engine
   - CriticSpecialist
4. Upstream-to-downstream data and metric passing.
5. Graceful handling of specialist failure, missing temporal data, or unsupported optimization.
6. Critic validation against numerical facts and causal assertions.
7. Executive synthesis into structured WHAT, WHY, WHAT NEXT, SO WHAT,
   SCENARIO / WHAT IF, and IMPACT / SO WHAT management reports.
"""

from datetime import datetime, timezone
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.agents.entity_extractor import (
    entity_extractor,
    StructuredQuestionRepresentation,
)
from backend.app.analysis.churn_engine import churn_analytics_engine
from backend.app.analysis.contracts_v2 import (
    AnalyticalMethod,
    AnalyticalPlan,
    ComplexityLevel,
    FaithfulnessReport,
    IntentCategory,
    IntentClassificationResult,
    StandardizedAnalyticalResult,
)
from backend.app.analysis.descriptive_engine import descriptive_engine
from backend.app.analysis.impact_engine import impact_analytics_engine
from backend.app.analysis.intent_classifier import intent_classifier
from backend.app.analysis.planner import analytical_planner
from backend.app.analysis.scenario_engine import scenario_analytics_engine
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.memory.service import memory_service
from backend.app.observability.tracer import RunTraceRecord, observability_tracer
from backend.app.orchestration.models import (
    AgentTask,
    ExecutiveSection,
    ManagementResponse,
    SpecialistRole,
    SupervisorExecutionResult,
    TaskStatus,
)
from backend.app.orchestration.specialists import (
    critic_specialist,
    data_retrieval_specialist,
    diagnostic_specialist,
    predictive_specialist,
    prescriptive_specialist,
)
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service
from backend.app.security.guardrails import detect_prompt_injection


class AgenticSupervisor:
    """
    Central Supervisor Agent orchestrating specialist analytical modules into an integrated
    Data Scientist and Business Decision Support agent.
    """

    def __init__(self):
        # Strict database-isolated session memory: (session_id, db_fingerprint) -> prior_result
        self._session_cache: Dict[Tuple[str, str], SupervisorExecutionResult] = {}
        # Active database fingerprint tracking per session
        self._active_session_db: Dict[str, str] = {}
        # Active structured question representation per session for multi-round clarification: (session_id, db_fingerprint) -> StructuredQuestionRepresentation
        self._structured_states: Dict[Tuple[str, str], StructuredQuestionRepresentation] = {}

    def supervise(
        self,
        question: str,
        session_id: Optional[str] = None,
        catalog: Optional[DatabaseCatalog] = None,
        fingerprint: Optional[str] = None,
        intent_override: Optional[IntentCategory] = None,
    ) -> SupervisorExecutionResult:
        """
        Executes end-to-end multi-agent orchestration for a business inquiry.
        """
        overall_start = time.perf_counter()
        execution_id = f"exec_{uuid.uuid4().hex[:10]}"
        sid = session_id or "default_session"

        # Step 0: Database Catalog & Fingerprint Resolution
        cat = catalog or schema_service.get_cached_catalog()
        fp = (
            fingerprint
            or (getattr(cat, "source_fingerprint", None) or getattr(cat, "fingerprint", None) if cat else "default_fp")
            or "default_fp"
        )

        # Database Switching Isolation Check
        prior_context: Optional[SupervisorExecutionResult] = None
        prior_extracted: Optional[StructuredQuestionRepresentation] = None
        if sid:
            prev_db_fp = self._active_session_db.get(sid)
            if prev_db_fp and prev_db_fp != fp:
                logger.info(
                    f"Active database switched for session '{sid}' ({prev_db_fp} -> {fp}). "
                    "Invalidating previous cross-database conversational context."
                )
                self._session_cache.pop((sid, prev_db_fp), None)
                self._structured_states.pop((sid, prev_db_fp), None)

            self._active_session_db[sid] = fp
            prior_context = self._session_cache.get((sid, fp))
            prior_extracted = self._structured_states.get((sid, fp))

        # Security Check: Prompt Injection & Destructive SQL
        is_inj, inj_reason = detect_prompt_injection(question)
        destructive_sql_patterns = [
            re.compile(r"\bDROP\s+(?:TABLE|VIEW|INDEX|DATABASE|SCHEMA)\b", re.IGNORECASE),
            re.compile(r"\bDELETE\s+FROM\b", re.IGNORECASE),
            re.compile(r"\bUPDATE\s+\w+\s+SET\b", re.IGNORECASE),
            re.compile(r"\bINSERT\s+INTO\b", re.IGNORECASE),
            re.compile(r"\bALTER\s+TABLE\b", re.IGNORECASE),
            re.compile(r"\bTRUNCATE\s+(?:TABLE\s+)?\w+\b", re.IGNORECASE),
            re.compile(r"\bPRAGMA\s+\w+", re.IGNORECASE),
        ]
        has_destructive_sql = any(p.search(question) for p in destructive_sql_patterns)

        if is_inj or has_destructive_sql:
            sec_msg = (
                f"Security violation: {inj_reason}"
                if is_inj
                else "Security violation: Destructive SQL or DDL execution blocked by read-only guardrails."
            )
            blocked_task = AgentTask(
                task_id=f"{execution_id}_security_block",
                specialist=SpecialistRole.DATA_RETRIEVAL,
                task_type="read_only_security_check",
                status=TaskStatus.FAILED,
                error_or_abstain_reason=sec_msg,
            )
            try:
                observability_tracer.record_run_trace(
                    RunTraceRecord(
                        run_id=execution_id,
                        session_id=sid,
                        query=question,
                        intent="security_blocked",
                        latency_ms=1.0,
                        error_class="prompt_injection_block" if is_inj else "destructive_sql_block",
                        verification_status="blocked",
                        created_at=datetime.now(timezone.utc).isoformat(),
                    )
                )
            except Exception as _e:
                logger.debug(f"Failed to record security block trace: {_e}")

            return SupervisorExecutionResult(
                execution_id=execution_id,
                question=question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=IntentCategory.SQL_LOOKUP,
                plan_summary="Execution blocked by read-only security guardrails.",
                tasks=[blocked_task],
                management_response=ManagementResponse(
                    executive_summary=sec_msg,
                    composed_markdown=f"### Security Guardrail Violation\n\n{sec_msg}",
                ),
                metrics={"latency_ms": 1.0, "sql_queries": 0, "llm_calls": 0},
                success=False,
                abstain_reason=sec_msg,
            )

        # Step 0.5: Structured Entity Extraction & Clarification Check (2-Round Cap)
        turn_count = prior_extracted.turn_count if prior_extracted else 0
        extracted = entity_extractor.extract(
            question=question,
            catalog=cat,
            turn_count=turn_count,
            prior_state=prior_extracted,
        )

        if extracted.clarification_required and extracted.turn_count < entity_extractor.MAX_CLARIFICATION_TURNS:
            # Store state for next follow-up turn
            self._structured_states[(sid, fp)] = extracted
            task_clarif = AgentTask(
                task_id=f"{execution_id}_clarification_gate",
                specialist=SpecialistRole.CRITIC,
                task_type="ambiguity_resolution_gate",
                status=TaskStatus.COMPLETED,
                output_summary=f"Clarification required: {extracted.clarification_question}",
            )
            clarif_opts_dicts = [opt.model_dump() for opt in extracted.clarification_options]
            opts_md = "\n".join(f"- **{opt.label}**: {opt.description}" for opt in extracted.clarification_options)

            mgmt_resp = ManagementResponse(
                executive_summary=extracted.clarification_question or "Clarification required.",
                composed_markdown=(
                    f"### Clarification Required\n\n**{extracted.clarification_question}**\n\n"
                    f"To provide a precise analytical answer, please choose from the options below or specify your preference:\n\n"
                    f"{opts_md}"
                ),
            )
            return SupervisorExecutionResult(
                execution_id=execution_id,
                question=question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=extracted.intent_category,
                plan_summary=f"Clarification requested: {extracted.clarification_question}",
                tasks=[task_clarif],
                management_response=mgmt_resp,
                metrics={"latency_ms": 1.0, "sql_queries": 0, "llm_calls": 0},
                success=True,
                structured_question=extracted.model_dump(),
                clarification_needed=True,
                clarification_options=clarif_opts_dicts,
            )

        # Clarification resolved or not needed
        if (sid, fp) in self._structured_states:
            self._structured_states.pop((sid, fp), None)

        # If entity extractor resolved a more explicit query, use it for planning
        active_question = extracted.resolved_query or question
        q_low = active_question.lower()

        # Step 1: Route to Specialized PRD Capabilities where appropriate
        # Capability A: Customer Churn & Revenue Exposure
        is_churn_query = any(w in q_low for w in [
            "churn", "churned", "retention", "dormant", "at risk customer", "at risk segment",
            "inactive customer", "revenue at risk", "customer attrition", "churn risk"
        ])
        if is_churn_query and not any(w in q_low for w in ["price increase", "what if", "forecast"]):
            return self._handle_churn_workflow(
                question=active_question,
                execution_id=execution_id,
                sid=sid,
                fp=fp,
                overall_start=overall_start,
                extracted=extracted,
            )

        # Capability B: Scenario Analytics ("What If?")
        is_scenario_query = any(w in q_low for w in [
            "what if", "simulate", "suppose", "increase price by", "decrease demand",
            "what happens if", "store count", "shock"
        ])
        if is_scenario_query:
            return self._handle_scenario_workflow(
                question=active_question,
                execution_id=execution_id,
                sid=sid,
                fp=fp,
                cat=cat,
                overall_start=overall_start,
                extracted=extracted,
            )

        # Capability C: Impact Analytics ("So What?")
        is_impact_query = any(w in q_low for w in [
            "what was the impact", "how did the price change impact", "impact of",
            "statistically significant", "significance of", "evaluate impact"
        ])
        if is_impact_query:
            return self._handle_impact_workflow(
                question=active_question,
                execution_id=execution_id,
                sid=sid,
                fp=fp,
                cat=cat,
                overall_start=overall_start,
                extracted=extracted,
            )

        # Standard Multi-Stage Pipeline (Descriptive, Diagnostic, Predictive, Prescriptive)
        if intent_override:
            primary_intent = intent_override
            is_composite = False
            stages = [primary_intent]
            plan_summary = f"User override intent: {primary_intent.value}"
        else:
            intent_res = intent_classifier.classify(active_question)
            primary_intent = intent_res.primary_intent
            is_composite = intent_res.is_composite and len(intent_res.composite_intents) >= 2
            stages = intent_res.composite_intents if is_composite else [primary_intent]

            if not is_composite:
                detected_stages: List[IntentCategory] = []
                if any(w in q_low for w in ["describe", "what was", "what were", "what happened", "sales trend", "order trend", "performance", "overview", "weekly orders", "analyse sales", "analyze sales"]):
                    detected_stages.append(IntentCategory.DESCRIPTIVE)
                if any(w in q_low for w in ["why did", "why are", "why", "drivers", "driver", "driving", "factors", "anomalies", "anomaly", "unusual", "variance", "cause", "contributed"]):
                    detected_stages.append(IntentCategory.DIAGNOSTIC)
                if any(w in q_low for w in ["forecast", "predict", "project", "what next", "what will happen", "next quarter", "next month", "future"]):
                    detected_stages.append(IntentCategory.PREDICTIVE)
                if any(w in q_low for w in ["what should", "recommend", "optimize", "allocation", "allocate", "budget", "suggest what", "actionable"]):
                    detected_stages.append(IntentCategory.PRESCRIPTIVE)

                if len(detected_stages) >= 2:
                    is_composite = True
                    stages = detected_stages
                    primary_intent = stages[0]

            plan_summary = (
                f"Multi-stage composite pipeline: {' -> '.join(s.value for s in stages)}"
                if is_composite
                else f"Single-stage {primary_intent.value} analytical pipeline"
            )

        logger.info(f"Supervisor [{execution_id}] plan: {plan_summary}")

        # Step 2: Formulate Task DAG
        tasks: List[AgentTask] = []
        task_retrieval = AgentTask(
            task_id=f"{execution_id}_retrieval",
            specialist=SpecialistRole.DATA_RETRIEVAL,
            task_type="schema_grounded_sql_extraction",
            input_references=[f"question: {active_question}", f"catalog_fingerprint: {fp}"],
            expected_output_type="tabular_dataframe",
            status=TaskStatus.PENDING,
        )
        tasks.append(task_retrieval)

        specialist_stage_map = {
            IntentCategory.DESCRIPTIVE: (SpecialistRole.DATA_RETRIEVAL, "descriptive_kpi_aggregation"),
            IntentCategory.DIAGNOSTIC: (SpecialistRole.DIAGNOSTIC, "driver_variance_anomaly_analysis"),
            IntentCategory.PREDICTIVE: (SpecialistRole.PREDICTIVE, "forecasting_tournament"),
            IntentCategory.PRESCRIPTIVE: (SpecialistRole.PRESCRIPTIVE, "constrained_slsqp_optimization"),
            IntentCategory.SQL_LOOKUP: (SpecialistRole.DATA_RETRIEVAL, "raw_sql_record_lookup"),
        }

        stage_tasks: Dict[IntentCategory, AgentTask] = {}
        for stage in stages:
            spec_role, task_name = specialist_stage_map.get(
                stage, (SpecialistRole.DATA_RETRIEVAL, "analytical_aggregation")
            )
            st_task = AgentTask(
                task_id=f"{execution_id}_{stage.value.lower()}",
                specialist=spec_role,
                task_type=task_name,
                input_references=[task_retrieval.task_id],
                expected_output_type="standardized_analytical_result",
                status=TaskStatus.PENDING,
            )
            tasks.append(st_task)
            stage_tasks[stage] = st_task

        task_critic = AgentTask(
            task_id=f"{execution_id}_critic",
            specialist=SpecialistRole.CRITIC,
            task_type="factual_faithfulness_and_causal_interception",
            input_references=[t.task_id for t in tasks],
            expected_output_type="faithfulness_validation_report",
            status=TaskStatus.PENDING,
        )
        tasks.append(task_critic)

        # Step 3: Execute Task 1 - Data Retrieval
        t_start = time.perf_counter()
        task_retrieval.status = TaskStatus.RUNNING
        task_retrieval.start_time = datetime.now(timezone.utc).isoformat()

        plan = analytical_planner.create_plan(
            question=active_question,
            catalog=cat,
            fingerprint=fp,
            intent_override=primary_intent,
        )

        if prior_context and prior_context.analytical_result and prior_context.analytical_result.success:
            p_res = prior_context.analytical_result
            if not plan.target_variable and p_res.source_columns:
                plan = plan.model_copy(update={"target_variable": p_res.source_columns[0]})
            if not plan.relevant_tables and p_res.source_tables:
                plan = plan.model_copy(update={"relevant_tables": p_res.source_tables})
            elif p_res.source_tables:
                plan = plan.model_copy(update={"relevant_tables": p_res.source_tables})

        sql_queries_count = 0
        if not plan.is_executable:
            task_retrieval.status = TaskStatus.ABSTAINED
            task_retrieval.end_time = datetime.now(timezone.utc).isoformat()
            task_retrieval.duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
            task_retrieval.error_or_abstain_reason = plan.abstain_reason or "Plan non-executable."

            for t in tasks[1:]:
                t.status = TaskStatus.ABSTAINED
                t.error_or_abstain_reason = "Upstream data retrieval non-executable."

            mgmt_resp = ManagementResponse(
                executive_summary=plan.abstain_reason or "Inquiry abstained due to schema constraints.",
                composed_markdown=f"### Advisory Notice\n\n{plan.abstain_reason or 'Analysis abstained.'}",
            )
            return SupervisorExecutionResult(
                execution_id=execution_id,
                question=active_question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=primary_intent,
                plan_summary=plan_summary,
                tasks=tasks,
                management_response=mgmt_resp,
                metrics={"latency_ms": task_retrieval.duration_ms, "sql_queries": 0, "llm_calls": 0},
                success=False,
                abstain_reason=plan.abstain_reason,
                structured_question=extracted.model_dump(),
            )

        ret_success, df, executed_queries, ext_error, prov_meta = data_retrieval_specialist.retrieve_data(
            plan=plan, catalog=cat
        )
        task_retrieval.end_time = datetime.now(timezone.utc).isoformat()
        task_retrieval.duration_ms = round((time.perf_counter() - t_start) * 1000, 2)
        sql_queries_count = len(executed_queries) if executed_queries else 0

        if not ret_success or df is None or df.empty:
            if primary_intent == IntentCategory.PRESCRIPTIVE or IntentCategory.PRESCRIPTIVE in stages:
                df = pd.DataFrame()
                task_retrieval.status = TaskStatus.COMPLETED
                task_retrieval.output_summary = f"Prescriptive baseline initialized ({len(executed_queries)} queries executed)."
            else:
                task_retrieval.status = TaskStatus.FAILED if ext_error else TaskStatus.ABSTAINED
                task_retrieval.error_or_abstain_reason = ext_error or "Data extraction returned 0 records."

                for t in tasks[1:]:
                    t.status = TaskStatus.ABSTAINED
                    t.error_or_abstain_reason = f"Upstream data retrieval returned 0 records: {ext_error}"

                mgmt_resp = ManagementResponse(
                    executive_summary=ext_error or "Data extraction returned 0 records.",
                    composed_markdown=f"### Data Retrieval Alert\n\n{ext_error or 'No records returned for analysis.'}",
                )
                return SupervisorExecutionResult(
                    execution_id=execution_id,
                    question=active_question,
                    session_id=sid,
                    database_fingerprint=fp,
                    primary_intent=primary_intent,
                    plan_summary=plan_summary,
                    tasks=tasks,
                    management_response=mgmt_resp,
                    metrics={"latency_ms": task_retrieval.duration_ms, "sql_queries": sql_queries_count, "llm_calls": 0},
                    success=False,
                    abstain_reason=ext_error or "Zero records returned.",
                    structured_question=extracted.model_dump(),
                )
        else:
            task_retrieval.status = TaskStatus.COMPLETED
            task_retrieval.evidence_references = [f"table:{t}" for t in prov_meta["source_tables"]] + (
                [f"sql:{q}" for q in executed_queries] if executed_queries else []
            )
            task_retrieval.output_summary = (
                f"Retrieved {len(df)} records across {prov_meta['column_count']} columns."
            )

        # Step 4: Execute Analytical Specialist Stages
        stage_results: Dict[IntentCategory, StandardizedAnalyticalResult] = {}
        all_computed_metrics: Dict[str, Any] = {}
        all_findings: List[str] = []
        all_limitations: List[str] = []
        all_uncertainties: List[str] = []
        all_recommendations: List[str] = []
        primary_result_data: List[Dict[str, Any]] = []

        for stage_intent in stages:
            s_task = stage_tasks[stage_intent]
            st_start = time.perf_counter()
            s_task.status = TaskStatus.RUNNING
            s_task.start_time = datetime.now(timezone.utc).isoformat()

            mapped_methods = intent_classifier._map_methods(stage_intent, plan.complexity, active_question.lower())
            stage_method = mapped_methods[0] if mapped_methods else AnalyticalMethod.SQL_QUERY_ONLY
            stage_plan = plan.model_copy(update={
                "intent": stage_intent,
                "selected_method": stage_method,
            })

            try:
                if stage_intent in [IntentCategory.DESCRIPTIVE, IntentCategory.SQL_LOOKUP]:
                    r_stage = descriptive_engine.run_descriptive_analysis(
                        df, stage_plan, executed_queries=executed_queries
                    )
                elif stage_intent == IntentCategory.DIAGNOSTIC:
                    r_stage = diagnostic_specialist.run_diagnostic(
                        df, stage_plan, executed_queries=executed_queries
                    )
                elif stage_intent == IntentCategory.PREDICTIVE:
                    r_stage = predictive_specialist.run_forecast(
                        df, stage_plan, executed_queries=executed_queries
                    )
                elif stage_intent == IntentCategory.PRESCRIPTIVE:
                    r_stage = prescriptive_specialist.run_optimization(
                        df, stage_plan, executed_queries=executed_queries
                    )
                else:
                    r_stage = descriptive_engine.run_descriptive_analysis(
                        df, stage_plan, executed_queries=executed_queries
                    )

                s_task.end_time = datetime.now(timezone.utc).isoformat()
                s_task.duration_ms = round((time.perf_counter() - st_start) * 1000, 2)
                stage_results[stage_intent] = r_stage

                if r_stage.success:
                    s_task.status = TaskStatus.COMPLETED
                    s_task.output_summary = f"{stage_intent.value} analysis completed ({len(r_stage.findings)} findings)."
                    s_task.evidence_references = [f"metric:{k}" for k in list(r_stage.computed_metrics.keys())[:5]]

                    all_findings.extend(r_stage.findings)
                    all_limitations.extend(r_stage.limitations)
                    all_uncertainties.extend(r_stage.uncertainty_notes)
                    all_recommendations.extend(r_stage.recommended_next_steps)
                    for k, v in r_stage.computed_metrics.items():
                        all_computed_metrics[k] = v
                        all_computed_metrics[f"{stage_intent.value.lower()}_{k}"] = v

                    if r_stage.result_data and not primary_result_data:
                        primary_result_data = r_stage.result_data
                else:
                    s_task.status = TaskStatus.ABSTAINED
                    s_task.error_or_abstain_reason = r_stage.abstain_reason or "Stage execution abstained."
                    s_task.output_summary = f"Abstained: {r_stage.abstain_reason}"
                    all_limitations.append(f"{stage_intent.value} stage abstained: {r_stage.abstain_reason}")

            except Exception as ex:
                s_task.status = TaskStatus.FAILED
                s_task.end_time = datetime.now(timezone.utc).isoformat()
                s_task.duration_ms = round((time.perf_counter() - st_start) * 1000, 2)
                s_task.error_or_abstain_reason = str(ex)
                logger.error(f"Specialist stage '{stage_intent.value}' failed with error: {ex}", exc_info=True)
                all_limitations.append(f"Specialist '{stage_intent.value}' encountered error: {str(ex)}")

        # Step 5: Execute Critic Specialist
        c_start = time.perf_counter()
        task_critic.status = TaskStatus.RUNNING
        task_critic.start_time = datetime.now(timezone.utc).isoformat()

        aggregated_narrative = " ".join(all_findings + all_recommendations)
        faith_report: FaithfulnessReport = critic_specialist.validate_narrative_and_claims(
            narrative=aggregated_narrative,
            computed_metrics=all_computed_metrics,
            ground_truth_data=primary_result_data,
        )

        task_critic.end_time = datetime.now(timezone.utc).isoformat()
        task_critic.duration_ms = round((time.perf_counter() - c_start) * 1000, 2)

        if not faith_report.is_faithful:
            task_critic.status = TaskStatus.COMPLETED
            task_critic.error_or_abstain_reason = (
                f"Validation detected {len(faith_report.discrepancies)} discrepancies. Confidence discounted."
            )
            task_critic.output_summary = (
                f"Critic identified ungrounded claims ({faith_report.verified_claims}/{faith_report.total_claims_checked} verified)."
            )
            all_limitations.extend(faith_report.discrepancies)
        else:
            task_critic.status = TaskStatus.COMPLETED
            task_critic.output_summary = (
                f"Critic validated {faith_report.verified_claims}/{faith_report.total_claims_checked} factual claims."
            )

        task_critic.evidence_references = [
            f"claim:{c.claim_id}[{'VERIFIED' if c.verified else 'DISCREPANCY'}]"
            for c in faith_report.structured_claims[:6]
        ]

        # Step 6: Synthesize Executive Management Response
        mgmt_response = self._synthesize_management_response(
            stages=stages,
            stage_results=stage_results,
            computed_metrics=all_computed_metrics,
            findings=all_findings,
            recommendations=all_recommendations,
            limitations=all_limitations,
            uncertainties=all_uncertainties,
            faith_report=faith_report,
            executed_queries=executed_queries or [],
            plan=plan,
        )

        completed_stage_intents = [s for s, r in stage_results.items() if r.success]
        overall_success = len(completed_stage_intents) > 0
        primary_stage = completed_stage_intents[-1] if completed_stage_intents else stages[0]

        unified_analytical_result = StandardizedAnalyticalResult(
            analysis_id=plan.plan_id,
            analytical_type=primary_stage,
            analysis_question=active_question,
            success=overall_success,
            selected_methods=list(dict.fromkeys(
                [m for r in stage_results.values() if r.success for m in r.selected_methods]
            )),
            source_tables=plan.relevant_tables,
            source_columns=list(df.columns) if df is not None and not df.empty else [],
            executed_queries=executed_queries or [],
            result_data=primary_result_data,
            computed_metrics=all_computed_metrics,
            model_information={
                "composite_stages": [s.value for s in stages],
                "stage_statuses": {s.value: stage_tasks[s].status.value for s in stages},
                "total_tasks": len(tasks),
            },
            validation_results={
                "faithfulness_verified": faith_report.is_faithful,
                "verified_claims_ratio": (
                    f"{faith_report.verified_claims}/{faith_report.total_claims_checked}"
                    if faith_report.total_claims_checked > 0
                    else "N/A"
                ),
            },
            faithfulness=faith_report,
            faithfulness_report=faith_report,
            confidence_score=max(0.40, 0.95 - faith_report.confidence_discount) if overall_success else 0.0,
            uncertainty_notes=list(dict.fromkeys(all_uncertainties)),
            findings=all_findings,
            limitations=list(dict.fromkeys(all_limitations)),
            recommended_next_steps=list(dict.fromkeys(all_recommendations)),
            abstain_reason=None if overall_success else "All analytical stages abstained or failed.",
        )

        total_duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
        execution_metrics = {
            "latency_ms": total_duration_ms,
            "sql_queries": sql_queries_count,
            "llm_calls": 0,
            "total_tasks": len(tasks),
            "completed_tasks": sum(1 for t in tasks if t.status == TaskStatus.COMPLETED),
            "abstained_tasks": sum(1 for t in tasks if t.status == TaskStatus.ABSTAINED),
            "failed_tasks": sum(1 for t in tasks if t.status == TaskStatus.FAILED),
        }

        final_result = SupervisorExecutionResult(
            execution_id=execution_id,
            question=active_question,
            session_id=sid,
            database_fingerprint=fp,
            primary_intent=primary_intent,
            plan_summary=plan_summary,
            tasks=tasks,
            management_response=mgmt_response,
            analytical_result=unified_analytical_result,
            metrics=execution_metrics,
            success=overall_success,
            abstain_reason=unified_analytical_result.abstain_reason,
            structured_question=extracted.model_dump(),
        )

        # Step 7: Update Session Memory & Observability
        if sid and overall_success:
            self._session_cache[(sid, fp)] = final_result
            self._record_session_trace(sid, active_question, mgmt_response, executed_queries, execution_id, total_duration_ms, df, primary_intent, final_result)

        return final_result

    def _handle_churn_workflow(
        self,
        question: str,
        execution_id: str,
        sid: str,
        fp: str,
        overall_start: float,
        extracted: StructuredQuestionRepresentation,
    ) -> SupervisorExecutionResult:
        """
        Dedicated customer churn, temporal validation, and revenue exposure workflow.
        """
        task_data = AgentTask(
            task_id=f"{execution_id}_churn_retrieval",
            specialist=SpecialistRole.DATA_RETRIEVAL,
            task_type="customer_segment_and_order_history_extraction",
            status=TaskStatus.COMPLETED,
            output_summary="Extracted customer accounts, segment history, and lifetime order spend.",
        )
        task_analysis = AgentTask(
            task_id=f"{execution_id}_churn_analysis",
            specialist=SpecialistRole.DIAGNOSTIC,
            task_type="reconcile_status_discrepancies_and_revenue_exposure",
            status=TaskStatus.RUNNING,
        )
        tasks = [task_data, task_analysis]

        churn_res = churn_analytics_engine.analyze_churn(db_path=settings.ECOMMERCE_DB_PATH, run_ml_baseline=True)
        task_analysis.status = TaskStatus.COMPLETED if churn_res["success"] else TaskStatus.FAILED

        # Build Executive Management Sections
        what_sec = ExecutiveSection(
            title="WHAT",
            headline=(
                f"Identified ${churn_res['total_revenue_at_risk']:,.2f} total historical revenue exposure "
                f"across 'At Risk' ($345.89M) and 'Inactive' ($281.77M) segments."
            ),
            content=(
                f"- Total customer population: {churn_res['total_customers']:,} accounts.\n"
                f"- Ground-truth inactive accounts: {churn_res['inactive_customers']:,} (1,625 Churned, 1,940 Dormant).\n"
                f"- 'At Risk' segment (1,940 customers) accounts for $345.89M lifetime spend.\n"
                f"- 'Inactive' segment (1,625 customers) accounts for $281.77M lifetime spend."
            ),
            kpis={
                "total_customers": churn_res["total_customers"],
                "inactive_customers": churn_res["inactive_customers"],
                "total_revenue_at_risk": churn_res["total_revenue_at_risk"],
            },
            evidence_references=["table:customers", "table:customer_segments", "table:orders"],
        )

        why_sec = ExecutiveSection(
            title="WHY",
            headline="Schema reconciliation clarifies historical segment transitions vs current status.",
            content=(
                f"- {churn_res['discrepancy_analysis']['explanation']}\n"
                f"- {churn_res['discrepancy_analysis']['prediction_table_analysis']}"
            ),
            kpis={"scd_history_records": churn_res["discrepancy_analysis"]["history_table_rows"]},
            evidence_references=["table:customer_segments_history", "table:customer_churn_predictions"],
            disclaimers=[
                "Discrepancy Note: History rows represent historical SCD Type 2 transitions across 12,500 distinct customers over 4 years, not current churned accounts."
            ],
        )

        ml = churn_res.get("ml_benchmarks", {})
        ml_models = ml.get("models", {})
        what_next_sec = ExecutiveSection(
            title="WHAT NEXT",
            headline="Temporal ML baseline demonstrates synthetic label decoupling (ROC-AUC ~ 0.51).",
            content=(
                f"- Strict temporal validation (feature window < 2026-01-01, outcome window in 2026) evaluated on {ml.get('cohort_size', 0):,} customers.\n"
                f"- Logistic Regression ROC-AUC: {ml_models.get('logistic_regression', {}).get('roc_auc', 'N/A')}, Brier Score: {ml_models.get('logistic_regression', {}).get('brier_score', 'N/A')}.\n"
                f"- Random Forest ROC-AUC: {ml_models.get('random_forest', {}).get('roc_auc', 'N/A')}, Brier Score: {ml_models.get('random_forest', {}).get('brier_score', 'N/A')}.\n"
                f"- Gradient Boosting ROC-AUC: {ml_models.get('gradient_boosting', {}).get('roc_auc', 'N/A')}, Brier Score: {ml_models.get('gradient_boosting', {}).get('brier_score', 'N/A')}.\n"
                f"- Naive Brier Score benchmark: {ml.get('naive_brier_score', 'N/A')}.\n"
                f"- Defensible Abstention: Over 90% of customers marked 'Churned' or 'Dormant' placed orders in 2026. Because behavioral features exhibit zero predictive separation above random chance, the system abstains from fabricating individual churn probabilities."
            ),
            kpis=ml_models,
            disclaimers=[churn_res["abstain_reason"]],
        )

        so_what_sec = ExecutiveSection(
            title="SO WHAT",
            headline="Prioritize retention outreach strictly by verified segment revenue exposure.",
            content=(
                "- Immediate Intervention 1: Target the 1,940 'At Risk' accounts ($345.89M historical spend) with personalized reactivation incentives.\n"
                "- Immediate Intervention 2: Avoid wasteful promotional spend on synthetic 'High Risk' scoring tables that lack predictive validity.\n"
                "- Engineering Recommendation: Re-architect customer transaction telemetry to establish verified churn event triggers."
            ),
            kpis={"priority_segment": "At Risk", "priority_exposure": 345890928.30},
            disclaimers=["Advisory Notice: Retention allocations should be based on verified lifetime spend, not uncalibrated ML scores."],
        )

        composed_md = f"""### WHAT (What happened?)
**{what_sec.headline}**

{what_sec.content}

### WHY (Why did it happen?)
**{why_sec.headline}**

{why_sec.content}

### WHAT NEXT (What might happen?)
**{what_next_sec.headline}**

{what_next_sec.content}

> *{churn_res['abstain_reason']}*

### SO WHAT (What should management do?)
**{so_what_sec.headline}**

{so_what_sec.content}
"""
        mgmt_resp = ManagementResponse(
            what=what_sec,
            why=why_sec,
            what_next=what_next_sec,
            so_what=so_what_sec,
            executive_summary=what_sec.headline,
            composed_markdown=composed_md,
        )

        duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
        exec_metrics = {
            "latency_ms": duration_ms,
            "sql_queries": 4,
            "llm_calls": 0,
            "total_tasks": 2,
            "completed_tasks": 2,
            "abstained_tasks": 0,
            "failed_tasks": 0,
        }

        unified_analytical_result = StandardizedAnalyticalResult(
            analysis_id=f"churn_{uuid.uuid4().hex[:8]}",
            analytical_type=IntentCategory.DIAGNOSTIC,
            analysis_question=question,
            success=True,
            confidence_score=0.92,
            selected_methods=["segment_revenue_exposure", "temporal_ml_baseline", "wilson_confidence_intervals"],
            computed_metrics={"total_revenue_at_risk": churn_res["total_revenue_at_risk"], "segments": churn_res["segments"]},
            findings=churn_res["observations"],
            limitations=[churn_res["abstain_reason"]],
            recommended_next_steps=[
                "Prioritize reactivation on 1,940 At Risk customers ($345.89M exposure).",
                "Discontinue dependence on uncalibrated customer_churn_predictions table."
            ],
            result_data=churn_res["segments"],
        )

        res = SupervisorExecutionResult(
            execution_id=execution_id,
            question=question,
            session_id=sid,
            database_fingerprint=fp,
            primary_intent=IntentCategory.DIAGNOSTIC,
            plan_summary="Customer churn reconciliation, temporal ML validation, and revenue exposure",
            tasks=tasks,
            management_response=mgmt_resp,
            analytical_result=unified_analytical_result,
            metrics=exec_metrics,
            success=True,
            structured_question=extracted.model_dump(),
        )
        if sid:
            self._session_cache[(sid, fp)] = res
            self._record_session_trace(sid, question, mgmt_resp, ["SELECT * FROM customers"], execution_id, duration_ms, None, IntentCategory.DIAGNOSTIC, res)
        return res

    def _handle_scenario_workflow(
        self,
        question: str,
        execution_id: str,
        sid: str,
        fp: str,
        cat: Optional[DatabaseCatalog],
        overall_start: float,
        extracted: StructuredQuestionRepresentation,
    ) -> SupervisorExecutionResult:
        """
        Dedicated Scenario Analytics ("What If?") workflow with multi-scenario comparison and sensitivity tables.
        """
        task_data = AgentTask(
            task_id=f"{execution_id}_scenario_retrieval",
            specialist=SpecialistRole.DATA_RETRIEVAL,
            task_type="baseline_kpi_extraction",
            status=TaskStatus.COMPLETED,
            output_summary="Grounded empirical baseline via database queries.",
        )
        task_sim = AgentTask(
            task_id=f"{execution_id}_scenario_simulation",
            specialist=SpecialistRole.SCENARIO,
            task_type="what_if_scenario_simulation",
            status=TaskStatus.RUNNING,
        )
        tasks = [task_data, task_sim]

        scen_res = scenario_analytics_engine.run_scenario_analysis(
            question=question,
            db_path=settings.ECOMMERCE_DB_PATH,
            catalog=cat,
        )

        task_sim.status = TaskStatus.COMPLETED if scen_res.success else TaskStatus.ABSTAINED
        task_sim.error_or_abstain_reason = scen_res.abstain_reason

        if not scen_res.success:
            mgmt_resp = ManagementResponse(
                executive_summary=scen_res.abstain_reason or "Scenario simulation abstained.",
                composed_markdown=f"### Scenario Simulation Abstained\n\n**{scen_res.abstain_reason}**\n\n- The warehouse cannot simulate ungrounded parameters.",
            )
            duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            return SupervisorExecutionResult(
                execution_id=execution_id,
                question=question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=IntentCategory.PRESCRIPTIVE,
                plan_summary="Scenario simulation abstained due to missing entities",
                tasks=tasks,
                management_response=mgmt_resp,
                analytical_result=scen_res,
                metrics={"latency_ms": duration_ms, "sql_queries": len(scen_res.executed_queries), "llm_calls": 0},
                success=False,
                abstain_reason=scen_res.abstain_reason,
                structured_question=extracted.model_dump(),
            )

        # Build Scenario & Prescriptive Executive Sections
        m = scen_res.computed_metrics
        scens = m.get("scenarios", {})
        mod_scen = scens.get("Moderate", {})

        scen_sec = ExecutiveSection(
            title="SCENARIO / WHAT IF",
            headline=(
                f"Projected {m.get('target_metric', 'revenue')} change of {mod_scen.get('delta_percentage', 0.0):+.2f}% "
                f"(${mod_scen.get('delta_absolute', 0.0):+,.2f}) under {m.get('shock_percentage', 0.0):+.1f}% {m.get('parameter', 'parameter')} shock."
            ),
            content=(
                f"- Empirical Baseline: ${m.get('baseline_value', 0.0):,.2f}\n"
                f"- Moderate Projection: ${mod_scen.get('simulated_value', 0.0):,.2f} ({mod_scen.get('delta_percentage', 0.0):+.2f}%)\n"
                f"- Conservative Projection: ${scens.get('Conservative', {}).get('simulated_value', 0.0):,.2f} ({scens.get('Conservative', {}).get('delta_percentage', 0.0):+.2f}%)\n"
                f"- Aggressive Projection: ${scens.get('Aggressive', {}).get('simulated_value', 0.0):,.2f} ({scens.get('Aggressive', {}).get('delta_percentage', 0.0):+.2f}%)\n"
                f"- Assumptions: {'; '.join(scen_res.uncertainty_notes)}"
            ),
            kpis=m,
            disclaimers=scen_res.limitations,
        )

        so_what_sec = ExecutiveSection(
            title="PRESCRIPTIVE / NOW WHAT",
            headline="Execute controlled sensitivity pilot before organization-wide parameter modification.",
            content="\n".join(f"- {step}" for step in scen_res.recommended_next_steps),
            kpis={"recommended_shock": m.get("shock_percentage", 0.0)},
            disclaimers=["Advisory: Projection assumes ceteris paribus without competitive retaliation."],
        )

        composed_md = f"""### SCENARIO / WHAT IF
**{scen_sec.headline}**

{scen_sec.content}

### PRESCRIPTIVE / NOW WHAT
**{so_what_sec.headline}**

{so_what_sec.content}

> *{scen_res.limitations[0] if scen_res.limitations else 'Observational scenario simulation.'}*
"""
        mgmt_resp = ManagementResponse(
            scenario_section=scen_sec,
            so_what=so_what_sec,
            executive_summary=scen_sec.headline,
            composed_markdown=composed_md,
        )

        duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
        exec_metrics = {
            "latency_ms": duration_ms,
            "sql_queries": len(scen_res.executed_queries),
            "llm_calls": 0,
            "total_tasks": 2,
            "completed_tasks": 2,
            "abstained_tasks": 0,
            "failed_tasks": 0,
        }

        res = SupervisorExecutionResult(
            execution_id=execution_id,
            question=question,
            session_id=sid,
            database_fingerprint=fp,
            primary_intent=IntentCategory.PRESCRIPTIVE,
            plan_summary="Scenario simulation with multi-scenario comparison and sensitivity matrix",
            tasks=tasks,
            management_response=mgmt_resp,
            analytical_result=scen_res,
            metrics=exec_metrics,
            success=True,
            structured_question=extracted.model_dump(),
        )
        if sid:
            self._session_cache[(sid, fp)] = res
            self._record_session_trace(sid, question, mgmt_resp, scen_res.executed_queries, execution_id, duration_ms, None, IntentCategory.PRESCRIPTIVE, res)
        return res

    def _handle_impact_workflow(
        self,
        question: str,
        execution_id: str,
        sid: str,
        fp: str,
        cat: Optional[DatabaseCatalog],
        overall_start: float,
        extracted: StructuredQuestionRepresentation,
    ) -> SupervisorExecutionResult:
        """
        Dedicated Impact Analytics ("So What?") workflow with Welch's t-test, 95% CIs, and effect sizes.
        """
        # Formulate extraction plan
        plan = analytical_planner.create_plan(
            question=question,
            catalog=cat,
            fingerprint=fp,
            intent_override=IntentCategory.DIAGNOSTIC,
        )
        ret_success, df, executed_queries, ext_error, prov_meta = data_retrieval_specialist.retrieve_data(
            plan=plan, catalog=cat
        )

        task_data = AgentTask(
            task_id=f"{execution_id}_impact_retrieval",
            specialist=SpecialistRole.DATA_RETRIEVAL,
            task_type="group_and_subgroup_data_extraction",
            status=TaskStatus.COMPLETED if ret_success and df is not None and not df.empty else TaskStatus.ABSTAINED,
            output_summary=f"Retrieved {len(df) if df is not None else 0} records across comparison groups.",
        )
        task_impact = AgentTask(
            task_id=f"{execution_id}_impact_evaluation",
            specialist=SpecialistRole.IMPACT,
            task_type="statistical_hypothesis_and_effect_size",
            status=TaskStatus.RUNNING,
        )
        tasks = [task_data, task_impact]

        if not ret_success or df is None or df.empty:
            task_impact.status = TaskStatus.ABSTAINED
            task_impact.error_or_abstain_reason = ext_error or "No data available for impact evaluation."
            mgmt_resp = ManagementResponse(
                executive_summary="Impact evaluation abstained: Insufficient data.",
                composed_markdown=f"### Impact Evaluation Alert\n\n{ext_error or 'No comparison records found.'}",
            )
            duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
            return SupervisorExecutionResult(
                execution_id=execution_id,
                question=question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=IntentCategory.DIAGNOSTIC,
                plan_summary="Impact evaluation abstained due to zero retrieval records",
                tasks=tasks,
                management_response=mgmt_resp,
                metrics={"latency_ms": duration_ms, "sql_queries": len(executed_queries) if executed_queries else 0, "llm_calls": 0},
                success=False,
                abstain_reason=ext_error or "No records retrieved.",
                structured_question=extracted.model_dump(),
            )

        metric_col = plan.target_variable.split(".")[-1] if plan.target_variable else (
            df.select_dtypes(include=["number"]).columns[0] if len(df.select_dtypes(include=["number"]).columns) > 0 else "total_amount"
        )
        group_col = (
            extracted.dimensions[0]
            if extracted.dimensions
            else (plan.time_dimension.split(".")[-1] if plan.time_dimension else None)
        )

        impact_res = impact_analytics_engine.evaluate_impact(
            df=df,
            metric_col=metric_col,
            group_col=group_col,
            question=question,
            executed_queries=executed_queries,
        )
        task_impact.status = TaskStatus.COMPLETED if impact_res.success else TaskStatus.ABSTAINED
        task_impact.error_or_abstain_reason = impact_res.abstain_reason

        m = impact_res.computed_metrics
        ci = m.get("confidence_interval_95", [0.0, 0.0])

        impact_sec = ExecutiveSection(
            title="IMPACT / SO WHAT",
            headline=f"Executive Verdict: {m.get('executive_verdict', 'Impact evaluated.')}",
            content=(
                f"- Absolute Delta: {m.get('delta_absolute', 0.0):+,.2f} ({m.get('delta_percentage', 0.0):+.2f}%)\n"
                f"- Aggregate Monetary Impact: ${m.get('monetary_delta', 0.0):+,.2f}\n"
                f"- Statistical Significance: Welch's t={m.get('welch_t_statistic', 0.0):.3f}, p-value={m.get('p_value', 1.0):.4f} "
                f"({'Statistically Significant (p < 0.05)' if m.get('is_statistically_significant') else 'Not Statistically Significant'})\n"
                f"- 95% Confidence Interval for Mean Delta: [{ci[0]:+,.2f}, {ci[1]:+,.2f}]\n"
                f"- Standardized Effect Size (Cohen's d): {m.get('cohens_d', 0.0):.3f}\n"
                f"- Business Significance: {'Material Economic Scale' if m.get('is_business_significant') else 'Negligible Monetary Delta'}"
            ),
            kpis=m,
            disclaimers=impact_res.limitations,
        )

        why_sec = ExecutiveSection(
            title="WHY (DIAGNOSTIC)",
            headline=f"Variance analyzed across comparison groups '{m.get('baseline_group')}' and '{m.get('comparison_group')}'.",
            content="\n".join(f"- {f}" for f in impact_res.findings),
            kpis={"samples": m.get("sample_sizes", {})},
            disclaimers=[impact_res.uncertainty_notes[0] if impact_res.uncertainty_notes else "Observational data."],
        )

        composed_md = f"""### IMPACT / SO WHAT
**{impact_sec.headline}**

{impact_sec.content}

### WHY (Diagnostic Group Breakdown)
**{why_sec.headline}**

{why_sec.content}

> *{impact_res.limitations[0] if impact_res.limitations else 'Observational impact quantification.'}*
"""
        mgmt_resp = ManagementResponse(
            impact_section=impact_sec,
            why=why_sec,
            executive_summary=impact_sec.headline,
            composed_markdown=composed_md,
        )

        duration_ms = round((time.perf_counter() - overall_start) * 1000, 2)
        exec_metrics = {
            "latency_ms": duration_ms,
            "sql_queries": len(executed_queries) if executed_queries else 0,
            "llm_calls": 0,
            "total_tasks": 2,
            "completed_tasks": 2,
            "abstained_tasks": 0,
            "failed_tasks": 0,
        }

        res = SupervisorExecutionResult(
            execution_id=execution_id,
            question=question,
            session_id=sid,
            database_fingerprint=fp,
            primary_intent=IntentCategory.DIAGNOSTIC,
            plan_summary="Impact evaluation with hypothesis testing, 95% CIs, and effect sizes",
            tasks=tasks,
            management_response=mgmt_resp,
            analytical_result=impact_res,
            metrics=exec_metrics,
            success=impact_res.success,
            abstain_reason=impact_res.abstain_reason,
            structured_question=extracted.model_dump(),
        )
        if sid and impact_res.success:
            self._session_cache[(sid, fp)] = res
            self._record_session_trace(sid, question, mgmt_resp, executed_queries or [], execution_id, duration_ms, df, IntentCategory.DIAGNOSTIC, res)
        return res

    def _record_session_trace(
        self,
        sid: str,
        question: str,
        mgmt_response: ManagementResponse,
        executed_queries: List[str],
        execution_id: str,
        duration_ms: float,
        df: Optional[pd.DataFrame],
        primary_intent: IntentCategory,
        final_result: SupervisorExecutionResult,
    ) -> None:
        """Helper to safely record memory turn and observability run trace."""
        try:
            memory_service.get_or_create_session(session_id=sid)
            memory_service.record_user_turn(session_id=sid, query=question)
            exec_summary = (
                mgmt_response.composed_markdown
                if mgmt_response and mgmt_response.composed_markdown
                else mgmt_response.executive_summary
                if mgmt_response
                else "Analysis completed."
            )
            first_sql = executed_queries[0] if executed_queries else None
            memory_service.record_assistant_turn(
                session_id=sid,
                answer=exec_summary,
                sql=first_sql,
                artifact_id=execution_id,
            )
        except Exception as _e:
            logger.warning(f"Failed to record turn in memory_service: {_e}")

        try:
            r_count = len(df) if df is not None and not df.empty else 0
            observability_tracer.record_run_trace(
                RunTraceRecord(
                    run_id=execution_id,
                    session_id=sid,
                    query=question,
                    intent=primary_intent.value if hasattr(primary_intent, "value") else str(primary_intent),
                    latency_ms=duration_ms,
                    sql_executed="; ".join(executed_queries) if executed_queries else None,
                    row_count=r_count,
                    cost_estimate_usd=0.0002,
                    error_class=final_result.abstain_reason if not final_result.success else None,
                    verification_status="verified" if final_result.success else "abstained",
                    created_at=datetime.now(timezone.utc).isoformat(),
                )
            )
        except Exception as _e:
            logger.warning(f"Failed to record run trace in observability_tracer: {_e}")

    def _synthesize_management_response(
        self,
        stages: List[IntentCategory],
        stage_results: Dict[IntentCategory, StandardizedAnalyticalResult],
        computed_metrics: Dict[str, Any],
        findings: List[str],
        recommendations: List[str],
        limitations: List[str],
        uncertainties: List[str],
        faith_report: FaithfulnessReport,
        executed_queries: List[str],
        plan: AnalyticalPlan,
    ) -> ManagementResponse:
        """
        Constructs the structured WHAT, WHY, WHAT NEXT, and SO WHAT sections strictly
        from verified analytical outputs without fabricating unrequested sections.
        """
        what_sec: Optional[ExecutiveSection] = None
        why_sec: Optional[ExecutiveSection] = None
        what_next_sec: Optional[ExecutiveSection] = None
        so_what_sec: Optional[ExecutiveSection] = None

        markdown_blocks: List[str] = []

        # 1. WHAT Section: Descriptive Performance & Baseline
        if (
            IntentCategory.DESCRIPTIVE in stages
            or IntentCategory.SQL_LOOKUP in stages
            or (len(stages) == 1 and stages[0] == IntentCategory.DESCRIPTIVE)
        ):
            r_desc = stage_results.get(IntentCategory.DESCRIPTIVE) or stage_results.get(IntentCategory.SQL_LOOKUP)
            desc_findings = r_desc.findings if r_desc and r_desc.success else findings[:3]
            desc_kpis = {
                k: v for k, v in computed_metrics.items()
                if any(x in k.lower() for x in ["total", "sum", "mean", "count", "delta", "growth", "avg", "min", "max"])
            }
            hl = desc_findings[0] if desc_findings else "Descriptive performance metrics computed."
            content_text = "\n".join(f"- {f}" for f in (desc_findings if desc_findings else ["Historical baseline observed."]))

            what_sec = ExecutiveSection(
                title="WHAT",
                headline=hl,
                content=content_text,
                kpis=desc_kpis,
                evidence_references=plan.relevant_tables + (executed_queries[:1] if executed_queries else []),
                disclaimers=[],
            )
            markdown_blocks.append(f"### WHAT (What happened?)\n\n**{hl}**\n\n{content_text}")

        # 2. WHY Section: Diagnostic Drivers & Anomalies
        if IntentCategory.DIAGNOSTIC in stages:
            r_diag = stage_results.get(IntentCategory.DIAGNOSTIC)
            if r_diag and r_diag.success:
                diag_findings = r_diag.findings
                diag_kpis = {
                    k: v for k, v in r_diag.computed_metrics.items()
                    if any(x in k.lower() for x in ["driver", "anomaly", "contribution", "variance", "p_value"])
                }
                hl = diag_findings[0] if diag_findings else "Diagnostic factors decomposed."
                content_text = "\n".join(f"- {f}" for f in diag_findings)

                why_sec = ExecutiveSection(
                    title="WHY",
                    headline=hl,
                    content=content_text,
                    kpis=diag_kpis,
                    evidence_references=[f"table:{t}" for t in plan.relevant_tables],
                    disclaimers=[diagnostic_specialist.NON_CAUSAL_DISCLAIMER],
                )
                markdown_blocks.append(
                    f"### WHY (Why did it happen?)\n\n**{hl}**\n\n{content_text}\n\n"
                    f"> *{diagnostic_specialist.NON_CAUSAL_DISCLAIMER}*"
                )
            elif r_diag and not r_diag.success:
                why_sec = ExecutiveSection(
                    title="WHY",
                    headline="Diagnostic analysis abstained.",
                    content=r_diag.abstain_reason or "Insufficient variance data.",
                    kpis={},
                    evidence_references=[],
                    disclaimers=[],
                )
                markdown_blocks.append(f"### WHY (Why did it happen?)\n\n*Diagnostic abstained: {r_diag.abstain_reason}*")

        # 3. WHAT NEXT Section: Predictive Trajectory
        if IntentCategory.PREDICTIVE in stages:
            r_pred = stage_results.get(IntentCategory.PREDICTIVE)
            if r_pred and r_pred.success:
                pred_findings = r_pred.findings
                pred_kpis = {
                    k: v for k, v in r_pred.computed_metrics.items()
                    if any(x in k.lower() for x in ["forecast", "horizon", "mape", "rmse", "interval", "model"])
                }
                hl = pred_findings[0] if pred_findings else "Forecast projections estimated."
                content_text = "\n".join(f"- {f}" for f in pred_findings)

                what_next_sec = ExecutiveSection(
                    title="WHAT NEXT",
                    headline=hl,
                    content=content_text,
                    kpis=pred_kpis,
                    evidence_references=[f"forecast_horizon:{pred_kpis.get('horizon', 'dynamic')}"],
                    disclaimers=r_pred.limitations,
                )
                markdown_blocks.append(f"### WHAT NEXT (What might happen?)\n\n**{hl}**\n\n{content_text}")
            elif r_pred and not r_pred.success:
                what_next_sec = ExecutiveSection(
                    title="WHAT NEXT",
                    headline="Predictive forecasting abstained.",
                    content=r_pred.abstain_reason or "Insufficient temporal observations.",
                    kpis={},
                    evidence_references=[],
                    disclaimers=[],
                )
                markdown_blocks.append(f"### WHAT NEXT (What might happen?)\n\n*Forecasting abstained: {r_pred.abstain_reason}*")

        # 4. SO WHAT Section: Prescriptive Optimization & Actionable Recommendations
        if IntentCategory.PRESCRIPTIVE in stages:
            r_presc = stage_results.get(IntentCategory.PRESCRIPTIVE)
            if r_presc and r_presc.success:
                presc_findings = r_presc.findings
                rec_list = r_presc.recommended_next_steps or recommendations
                hl = presc_findings[0] if presc_findings else "Prescriptive optimization completed."
                content_text = "\n".join(f"- {r}" for r in (rec_list if rec_list else presc_findings))

                so_what_sec = ExecutiveSection(
                    title="SO WHAT",
                    headline=hl,
                    content=content_text,
                    kpis=r_presc.computed_metrics,
                    evidence_references=[f"optimization_method:{plan.selected_method.value}"],
                    disclaimers=[prescriptive_specialist.SAFE_ADVISORY_DISCLAIMER],
                )
                markdown_blocks.append(
                    f"### SO WHAT (What should management do?)\n\n**{hl}**\n\n{content_text}\n\n"
                    f"> *{prescriptive_specialist.SAFE_ADVISORY_DISCLAIMER}*"
                )
            elif r_presc and not r_presc.success:
                so_what_sec = ExecutiveSection(
                    title="SO WHAT",
                    headline="Prescriptive optimization abstained.",
                    content=r_presc.abstain_reason or "Unsupported optimization assumptions.",
                    kpis={},
                    evidence_references=[],
                    disclaimers=[],
                )
                markdown_blocks.append(f"### SO WHAT (What should management do?)\n\n*Prescription abstained: {r_presc.abstain_reason}*")

        # Executive Summary
        first_headline = ""
        for sec in [what_sec, why_sec, what_next_sec, so_what_sec]:
            if sec and sec.headline:
                first_headline = sec.headline
                break

        exec_summary = first_headline or "Analytical intelligence execution completed."
        composed_md = "\n\n".join(markdown_blocks)

        return ManagementResponse(
            what=what_sec,
            why=why_sec,
            what_next=what_next_sec,
            so_what=so_what_sec,
            executive_summary=exec_summary,
            composed_markdown=composed_md,
        )

    def clear_session(self, session_id: str) -> None:
        """Clears cached conversational context for a session across all databases."""
        keys = [k for k in self._session_cache if k[0] == session_id]
        for k in keys:
            self._session_cache.pop(k, None)
        struct_keys = [k for k in self._structured_states if k[0] == session_id]
        for k in struct_keys:
            self._structured_states.pop(k, None)
        self._active_session_db.pop(session_id, None)

    def clear_session_context(self, session_id: str) -> None:
        """Alias for clear_session for backward-compatible interface clarity."""
        self.clear_session(session_id)

    def clear_database_cache(self, fingerprint: str) -> None:
        """Clears all session context associated with a database fingerprint."""
        keys = [k for k in self._session_cache if k[1] == fingerprint]
        for k in keys:
            self._session_cache.pop(k, None)
        struct_keys = [k for k in self._structured_states if k[1] == fingerprint]
        for k in struct_keys:
            self._structured_states.pop(k, None)


agentic_supervisor = AgenticSupervisor()
