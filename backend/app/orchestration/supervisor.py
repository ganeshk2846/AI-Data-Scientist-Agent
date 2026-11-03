"""
backend/app/orchestration/supervisor.py
Phase 5: Agentic Supervisor for Autonomous Analytical Decision Support.

Coordinates:
1. Question understanding & multi-intent analytical planning (1-to-4 stage workflows).
2. Database-isolated conversational session context strictly keyed to (session_id, db_fingerprint).
3. Dependency-aware task routing across 5 Specialist Analytical Agents:
   - DataRetrievalSpecialist
   - DiagnosticSpecialist
   - PredictiveSpecialist
   - PrescriptiveSpecialist
   - CriticSpecialist
4. Upstream-to-downstream data and metric passing.
5. Graceful handling of specialist failure, missing temporal data, or unsupported optimization.
6. Critic validation against numerical facts and causal assertions.
7. Executive synthesis into structured WHAT, WHY, WHAT NEXT, and SO WHAT management reports.
"""

from datetime import datetime, timezone
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

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
from backend.app.analysis.intent_classifier import intent_classifier
from backend.app.analysis.planner import analytical_planner
from backend.app.core.logging import logger
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
        if sid:
            prev_db_fp = self._active_session_db.get(sid)
            if prev_db_fp and prev_db_fp != fp:
                logger.info(
                    f"Active database switched for session '{sid}' ({prev_db_fp} -> {fp}). "
                    "Invalidating previous cross-database conversational context."
                )
                self._session_cache.pop((sid, prev_db_fp), None)

            self._active_session_db[sid] = fp
            prior_context = self._session_cache.get((sid, fp))

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

        # Step 1: Intent & Multi-Stage Analytical Planning
        if intent_override:
            primary_intent = intent_override
            is_composite = False
            stages = [primary_intent]
            plan_summary = f"User override intent: {primary_intent.value}"
        else:
            intent_res = intent_classifier.classify(question)
            primary_intent = intent_res.primary_intent
            is_composite = intent_res.is_composite and len(intent_res.composite_intents) >= 2
            stages = intent_res.composite_intents if is_composite else [primary_intent]

            # Supervisor composite refinement if classifier didn't flag multi-stage cues
            if not is_composite:
                q_low = question.lower()
                detected_stages: List[IntentCategory] = []

                if any(w in q_low for w in ["describe", "what was", "what were", "what happened", "sales trend", "performance", "overview", "analyse sales", "analyze sales"]):
                    detected_stages.append(IntentCategory.DESCRIPTIVE)

                if any(w in q_low for w in ["why did", "why are", "why", "drivers", "factors", "anomalies", "variance", "cause", "contributed"]):
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

        # Task 1: Schema-Grounded Data Retrieval
        task_retrieval = AgentTask(
            task_id=f"{execution_id}_retrieval",
            specialist=SpecialistRole.DATA_RETRIEVAL,
            task_type="schema_grounded_sql_extraction",
            input_references=[f"question: {question}", f"catalog_fingerprint: {fp}"],
            expected_output_type="tabular_dataframe",
            status=TaskStatus.PENDING,
        )
        tasks.append(task_retrieval)

        # Specialist Tasks 2..K (ordered sequentially according to dependency requirements)
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

        # Final Task: Critic Validation
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

        # Create Schema-Grounded Analytical Plan
        plan = analytical_planner.create_plan(
            question=question,
            catalog=cat,
            fingerprint=fp,
            intent_override=primary_intent,
        )

        # Ground follow-up turn context if available in same database
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
                question=question,
                session_id=sid,
                database_fingerprint=fp,
                primary_intent=primary_intent,
                plan_summary=plan_summary,
                tasks=tasks,
                management_response=mgmt_resp,
                metrics={"latency_ms": task_retrieval.duration_ms, "sql_queries": 0, "llm_calls": 0},
                success=False,
                abstain_reason=plan.abstain_reason,
            )

        # Invoke DataRetrievalSpecialist
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
                    question=question,
                    session_id=sid,
                    database_fingerprint=fp,
                    primary_intent=primary_intent,
                    plan_summary=plan_summary,
                    tasks=tasks,
                    management_response=mgmt_resp,
                    metrics={"latency_ms": task_retrieval.duration_ms, "sql_queries": sql_queries_count, "llm_calls": 0},
                    success=False,
                    abstain_reason=ext_error or "Zero records returned.",
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

            mapped_methods = intent_classifier._map_methods(stage_intent, plan.complexity, question.lower())
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

        # Step 6: Synthesize Executive Management Response (WHAT, WHY, WHAT NEXT, SO WHAT)
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

        # Assemble unified StandardizedAnalyticalResult
        completed_stage_intents = [s for s, r in stage_results.items() if r.success]
        overall_success = len(completed_stage_intents) > 0
        primary_stage = completed_stage_intents[-1] if completed_stage_intents else stages[0]

        unified_analytical_result = StandardizedAnalyticalResult(
            analysis_id=plan.plan_id,
            analytical_type=primary_stage,
            analysis_question=question,
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
            question=question,
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
        )

        # Step 7: Update Database-Isolated Conversational Context
        if sid and overall_success:
            self._session_cache[(sid, fp)] = final_result

        return final_result

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
        self._active_session_db.pop(session_id, None)

    def clear_database_cache(self, fingerprint: str) -> None:
        """Clears all session context associated with a database fingerprint."""
        keys = [k for k in self._session_cache if k[1] == fingerprint]
        for k in keys:
            self._session_cache.pop(k, None)


agentic_supervisor = AgenticSupervisor()
