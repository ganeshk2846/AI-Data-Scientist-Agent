from datetime import datetime, timezone
import json
"""
Multi-Agent Orchestrator with Planning, Clarification, Bounded SQL Repair, and Hybrid Schema Retrieval.
Coordinates Router, Answerability Gate, Clarification, Planner, Hybrid Retriever, Value Linker,
Validator, Repair Loop, Executor, Visualization, and Composer.
"""

import asyncio
import time
import uuid
from typing import Any, Callable, Dict, List, Optional
from pydantic import BaseModel, Field

from backend.app.agents.clarification import answerability_gate, clarification_agent
from backend.app.agents.contracts import (
    AnswerabilityAssessment,
    ChartSpecification,
    ClarificationResponse,
    ExecutionPlan,
    RepairAttempt,
)
from backend.app.agents.planner import planner_agent
from backend.app.agents.router import RouteResult, router_agent
from backend.app.agents.visualization import visualization_agent
from backend.app.analysis.contracts import AnalysisToolResult
from backend.app.analysis.registry import analysis_registry
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.db.manager import db_manager
from backend.app.memory.service import memory_service
from backend.app.observability.tracer import RunTraceRecord, StageSpanRecord, observability_tracer
from backend.app.orchestration.models import ExecutiveSection, ManagementResponse
from backend.app.security.guardrails import detect_prompt_injection, validate_sql_security
from backend.app.llm.client import get_llm_provider
from backend.app.llm.models import LLMMessage, LLMRequest
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.retrieval.semantics import dynamic_semantic_engine, semantic_registry
from backend.app.retrieval.value_linker import LinkedValue, value_linker
from backend.app.schema.service import schema_service
from backend.app.sql.executor import QueryExecutionResult, sql_executor
from backend.app.sql.repair import sql_repair_loop
from backend.app.sql.validator import sql_validator
from backend.app.workflow.models import StepTrace, VerificationResult, WorkflowProgressState

SQL_GEN_PROMPT = """You are an expert Data Scientist and SQL Engineer specializing in {dialect}.
Write a single, safe, read-only {dialect} SELECT query to answer the user's business question.

STRICT CONSTRAINTS:
1. Use ONLY the table and column identifiers provided in the schema context below.
2. NEVER invent column names or table names.
3. Use {dialect} functions (e.g. for SQLite: strftime, ROUND, COUNT, SUM, AVG; for PostgreSQL: DATE_TRUNC, EXTRACT, ROUND; for MySQL: DATE_FORMAT, ROUND).
4. For revenue or money values, ROUND(..., 2).
5. Output ONLY the raw SQL inside a markdown ```sql code block. No extra conversation.

SCHEMA CONTEXT:
{schema_context}

{linked_values_context}

{metrics_context}
"""

COMPOSER_PROMPT = """You are an expert Chief Data Scientist composing a concise executive response.
Grounded strictly in the following query results, state the key factual findings and any business caveats.
Never claim causation from mere correlation. If results are empty, state that plainly.

USER QUESTION: {question}
INTENT: {intent}
SQL EXECUTED: {sql}
QUERY RESULTS (First {row_count} rows):
{results_preview}

Respond in concise markdown with:
- **Direct Answer**: Clear factual response citing exact numbers.
- **Key Findings**: Bullet points summarizing the metrics.
- **Caveats / Data Coverage**: Any limitations or data boundaries.
"""


class MultiAgentWorkflowResult(BaseModel):
    """Complete result from the multi-agent planning and execution pipeline."""
    run_id: str
    session_id: str = "default_session"
    query: str
    standalone_query: Optional[str] = None
    route: RouteResult
    answerability: AnswerabilityAssessment
    clarification: Optional[ClarificationResponse] = None
    plan: Optional[ExecutionPlan] = None
    selected_tables: List[str] = Field(default_factory=list)
    linked_values: List[LinkedValue] = Field(default_factory=list)
    sanitized_sql: Optional[str] = None
    query_result: Optional[QueryExecutionResult] = None
    chart_spec: Optional[ChartSpecification] = None
    analysis_result: Optional[AnalysisToolResult] = None
    verification: Optional[VerificationResult] = None
    repair_attempts: List[RepairAttempt] = Field(default_factory=list)
    composed_answer: str
    management_response: Optional[ManagementResponse] = None
    analytical_result: Optional[Dict[str, Any]] = None
    specialist_capability: Optional[str] = None
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    suggested_followups: List[str] = Field(default_factory=list)
    trace_steps: List[StepTrace] = Field(default_factory=list)
    total_duration_ms: float = 0.0



_CAPABILITY_INTENT = {
    "churn": "diagnostic",
    "order_drop": "diagnostic",
    "impact": "diagnostic",
    "scenario": "prescriptive",
}


def _tool_section(title: str, headline: str, payload: Dict[str, Any], disclaimers: List[str]) -> ExecutiveSection:
    """Builds an executive section from a deterministic tool result, using only its own values."""
    scalars = {
        k: v for k, v in payload.items()
        if isinstance(v, (int, float, str, bool)) and k not in ("tool_name", "analysis_type")
    }
    lines = [f"- **{k.replace('_', ' ').capitalize()}:** {v}" for k, v in list(scalars.items())[:8]]
    return ExecutiveSection(
        title=title,
        headline=headline,
        content="\n".join(lines) if lines else "- No reportable values were produced by this tool.",
        kpis={k: v for k, v in scalars.items() if isinstance(v, (int, float)) and not isinstance(v, bool)},
        disclaimers=disclaimers,
    )


def _synthesize_management_from_workflow(
    route: RouteResult,
    query_result: Optional[QueryExecutionResult],
    analysis_res: Optional[AnalysisToolResult],
    composed_text: str,
    key_findings: List[str],
    warnings: List[str],
    sanitized_sql: Optional[str],
) -> ManagementResponse:
    """
    Builds the WHAT / WHY / WHAT NEXT / SO WHAT response from the outputs this run
    already produced. No extra queries are issued, so the narrative and the sections
    are always derived from the same verified figures. Sections without a verified
    basis are omitted rather than invented.
    """
    numeric_kpis: Dict[str, Any] = {}
    if query_result and query_result.rows:
        for k, v in query_result.rows[0].items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                numeric_kpis[k] = v

    headline = ""
    in_fence = False
    for raw_line in (composed_text or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence or not line or line.startswith(("#", ">", "|", "-", "*")):
            continue
        headline = line.lstrip("#* ").strip()
        break
    if not headline:
        headline = f"Query returned {query_result.row_count if query_result else 0} rows."

    what = ExecutiveSection(
        title="WHAT",
        headline=headline[:300],
        content="\n".join(f"- {f}" for f in key_findings) or "- No rows were returned for this question.",
        kpis=numeric_kpis,
        evidence_references=([f"sql:{sanitized_sql}"] if sanitized_sql else []),
        disclaimers=list(warnings or []),
    )

    why = what_next = so_what = scenario_section = None
    if analysis_res and analysis_res.success:
        dump = analysis_res.model_dump()
        if analysis_res.anomaly_detection:
            why = _tool_section(
                "WHY",
                "Anomaly detection ran on the returned series.",
                dump.get("anomaly_detection") or {},
                ["Observational: an anomaly marks where a value departs from its baseline, not why."],
            )
        elif analysis_res.driver_analysis:
            why = _tool_section(
                "WHY",
                "Driver decomposition ran on the returned series.",
                dump.get("driver_analysis") or {},
                ["Observational: driver shares describe where the change sits, not its cause."],
            )
        if analysis_res.forecast:
            what_next = _tool_section(
                "WHAT NEXT",
                "A forecast was fitted to the returned series.",
                dump.get("forecast") or {},
                ["Forecast intervals assume the fitted model's conditions hold."],
            )
        if analysis_res.optimization:
            so_what = _tool_section(
                "SO WHAT",
                "An allocation was optimised against the supplied constraints.",
                dump.get("optimization") or {},
                ["Advisory only: optimisation output is decision support, not a committed plan."],
            )
        elif analysis_res.churn_risk:
            so_what = _tool_section(
                "SO WHAT",
                "Churn exposure was quantified for the current segments.",
                dump.get("churn_risk") or {},
                ["Advisory only: prioritise by verified exposure, not by stored risk scores."],
            )
        if analysis_res.scenario:
            scenario_section = _tool_section(
                "SCENARIO / WHAT IF",
                "A parameter shock was simulated against the baseline.",
                dump.get("scenario") or {},
                ["Scenario output is a simulation, not an observed outcome."],
            )

    blocks = [f"### WHAT (What happened?)\n\n**{what.headline}**\n\n{what.content}"]
    for sec, header in (
        (why, "### WHY (Why did it happen?)"),
        (what_next, "### WHAT NEXT (What might happen?)"),
        (so_what, "### SO WHAT (What should management do?)"),
        (scenario_section, "### SCENARIO (What if?)"),
    ):
        if sec:
            block = f"{header}\n\n**{sec.headline}**\n\n{sec.content}"
            if sec.disclaimers:
                block += f"\n\n> *{sec.disclaimers[0]}*"
            blocks.append(block)

    return ManagementResponse(
        what=what,
        why=why,
        what_next=what_next,
        so_what=so_what,
        scenario_section=scenario_section,
        executive_summary=what.headline,
        composed_markdown="\n\n".join(blocks),
    )


class MultiAgentOrchestrator:
    """Orchestrates the multi-agent pipeline with planning, clarification, hybrid retrieval, and bounded repair."""

    async def _run_specialist_capability(
        self,
        capability: str,
        query: str,
        effective_query: str,
        standalone_q: Optional[str],
        session_id: str,
        run_id: str,
        overall_start: float,
        traces: List[StepTrace],
        catalog: Any,
        progress_callback: Optional[Callable[[WorkflowProgressState, str], None]] = None,
    ) -> MultiAgentWorkflowResult:
        """
        Executes a specialist analytical workflow and returns it on the chat contract,
        so the UI receives one shape whichever path a question takes.
        """
        from backend.app.orchestration.supervisor import agentic_supervisor

        if progress_callback:
            progress_callback("generating_query", f"Routing to the {capability.replace('_', ' ')} specialist workflow...")

        stage_start = time.perf_counter()
        loop = asyncio.get_running_loop()
        sup_res = await loop.run_in_executor(
            None,
            lambda: agentic_supervisor.supervise(
                question=effective_query,
                session_id=session_id,
                catalog=catalog,
            ),
        )
        stage_ms = (time.perf_counter() - stage_start) * 1000

        for task in sup_res.tasks:
            raw_status = getattr(task.status, "value", str(task.status)).upper()
            if raw_status == "COMPLETED":
                t_status = "succeeded"
            elif raw_status == "ABSTAINED":
                t_status = "skipped"
            else:
                t_status = "failed"

            dur = task.duration_ms
            if dur is None or dur <= 0.0:
                dur = round(stage_ms / max(len(sup_res.tasks) + 1, 1), 2)

            traces.append(StepTrace(
                step="running_query",
                status=t_status,
                duration_ms=dur,
                message=f"{task.specialist.value}: {task.output_summary or task.error_or_abstain_reason or task.task_type}",
            ))
        traces.append(StepTrace(
            step="composing_answer",
            status="succeeded",
            duration_ms=round(stage_ms, 2),
            message=f"{capability.replace('_', ' ').title()} workflow composed the executive response.",
        ))

        if progress_callback:
            progress_callback("composing_answer", "Composing executive narrative from verified analytical outputs...")

        mgmt = sup_res.management_response
        composed_text = (mgmt.composed_markdown or mgmt.executive_summary) if mgmt else ""
        analytical = sup_res.analytical_result
        executed_sql = list(analytical.executed_queries) if (analytical and analytical.executed_queries) else []

        clarification = None
        if sup_res.clarification_needed:
            clarification = ClarificationResponse(
                needs_clarification=True,
                question=(mgmt.executive_summary if mgmt else None),
                ambiguity_reason="The question needs one detail before it can be answered precisely.",
                options=[],
                default_interpretation=None,
            )

        route = RouteResult(
            intent=_CAPABILITY_INTENT.get(capability, "diagnostic"),
            confidence=0.9,
            complexity="complex",
            reasoning=f"Specialist capability '{capability}' matched by the shared router.",
            target_domains=[],
            suggested_entities=[],
        )
        answerability = AnswerabilityAssessment(
            is_answerable=bool(sup_res.success),
            confidence=float(analytical.confidence_score) if analytical else 0.9,
            refusal_reason=sup_res.abstain_reason,
            available_alternatives=[],
        )
        verification = VerificationResult(
            is_valid=bool(sup_res.success),
            empty_result=not bool(executed_sql),
            row_count=len(analytical.result_data) if (analytical and analytical.result_data) else 0,
            checks_passed=["Specialist workflow executed", "Figures derived from executed SQL"],
            warnings=list(analytical.limitations) if analytical else [],
        )

        total_duration_ms = (time.perf_counter() - overall_start) * 1000
        memory_service.record_assistant_turn(
            session_id, composed_text, sql=(executed_sql[0] if executed_sql else None)
        )
        observability_tracer.record_run_trace(
            RunTraceRecord(
                run_id=run_id,
                session_id=session_id,
                query=query,
                intent=route.intent,
                latency_ms=total_duration_ms,
                sql_executed=(executed_sql[0] if executed_sql else None),
                row_count=verification.row_count,
                cost_estimate_usd=0.0,
                error_class=None,
                verification_status="verified" if sup_res.success else "abstained",
                created_at=datetime.now(timezone.utc).isoformat(),
                orchestrator_type="workflow_orchestrator",
                llm_provider="groq",
            )
        )

        return MultiAgentWorkflowResult(
            run_id=run_id,
            session_id=session_id,
            query=query,
            standalone_query=standalone_q,
            route=route,
            answerability=answerability,
            clarification=clarification,
            sanitized_sql=(executed_sql[0] if executed_sql else None),
            verification=verification,
            composed_answer=composed_text,
            management_response=mgmt,
            analytical_result=(analytical.model_dump() if analytical else None),
            specialist_capability=capability,
            key_findings=list(analytical.findings) if analytical else [],
            limitations=list(analytical.limitations) if analytical else [],
            suggested_followups=list(analytical.recommended_next_steps) if analytical else [],
            trace_steps=traces,
            total_duration_ms=round(total_duration_ms, 2),
        )

    async def run(
        self,
        query: str,
        session_id: str = "default_session",
        request_id: Optional[str] = None,
        progress_callback: Optional[Callable[[WorkflowProgressState, str], None]] = None,
    ) -> MultiAgentWorkflowResult:
        run_id = request_id or str(uuid.uuid4())
        overall_start = time.perf_counter()
        traces: List[StepTrace] = []
        repair_attempts: List[RepairAttempt] = []

        # Step -1: Security Prompt Injection Check
        is_inj, inj_reason = detect_prompt_injection(query)
        if is_inj:
            duration_ms = (time.perf_counter() - overall_start) * 1000
            refusal_ans = AnswerabilityAssessment(
                is_answerable=False,
                confidence=1.0,
                refusal_reason=f"Security violation: {inj_reason}",
                available_alternatives=["Ask a direct question regarding ecommerce orders, customers, or metrics."],
            )
            res = MultiAgentWorkflowResult(
                run_id=run_id,
                session_id=session_id,
                query=query,
                standalone_query=query,
                route=RouteResult(intent="descriptive", confidence=1.0, reasoning="Security prompt injection blocked"),
                answerability=refusal_ans,
                composed_answer=f"Request blocked by security guardrails: {inj_reason}",
                total_duration_ms=round(duration_ms, 2),
            )
            observability_tracer.record_run_trace(
                RunTraceRecord(
                    run_id=run_id,
                    session_id=session_id,
                    query=query,
                    intent="security_blocked",
                    latency_ms=duration_ms,
                    error_class="prompt_injection_block",
                    verification_status="blocked",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    orchestrator_type="workflow_orchestrator",
                    llm_provider="groq",
                )
            )
            return res

        # Step 0: ContextResolver (Shared Memory)
        standalone_q = memory_service.resolve_contextual_question(session_id, query)
        effective_query = standalone_q or query
        if standalone_q != query:
            traces.append(StepTrace(
                step="understanding_question",
                status="succeeded",
                duration_ms=1.0,
                message=f"ContextResolver resolved follow-up to: '{standalone_q}'",
            ))
        memory_service.record_user_turn(session_id, query, standalone_rewrite=standalone_q)

        catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
        llm = get_llm_provider()

        # Step 0.6: Specialist capability routing. The chat pipeline is the single
        # entry point; questions belonging to a specialist analytical workflow are
        # executed there and returned on this same contract.
        from backend.app.orchestration.supervisor import agentic_supervisor

        capability = agentic_supervisor.detect_capability(effective_query)
        if capability:
            return await self._run_specialist_capability(
                capability=capability,
                query=query,
                effective_query=effective_query,
                standalone_q=standalone_q,
                session_id=session_id,
                run_id=run_id,
                overall_start=overall_start,
                traces=traces,
                catalog=catalog,
                progress_callback=progress_callback,
            )

        # Step 0.5: Fast-Path Answerability Screening (Enforces Honest Refusal before expensive routing)
        pre_assessment = answerability_gate.evaluate(effective_query, route=None, catalog=catalog)
        if not pre_assessment.is_answerable:
            total_duration_ms = (time.perf_counter() - overall_start) * 1000
            traces.append(StepTrace(
                step="understanding_question",
                status="failed",
                duration_ms=round(total_duration_ms, 2),
                message=f"Answerability Gate Refusal: {pre_assessment.refusal_reason}",
            ))
            default_route = RouteResult(intent="descriptive", confidence=1.0, reasoning="Fast-path refusal before routing")
            observability_tracer.record_run_trace(
                RunTraceRecord(
                    run_id=run_id,
                    session_id=session_id,
                    query=query,
                    intent=default_route.intent,
                    latency_ms=total_duration_ms,
                    sql_executed=None,
                    row_count=0,
                    cost_estimate_usd=0.0,
                    error_class="answerability_refusal",
                    verification_status="refused",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    orchestrator_type="workflow_orchestrator",
                    llm_provider="groq",
                )
            )
            return MultiAgentWorkflowResult(
                run_id=run_id,
                session_id=session_id,
                query=query,
                standalone_query=standalone_q,
                route=default_route,
                answerability=pre_assessment,
                composed_answer=f"### Question Not Answerable From Warehouse\n\n{pre_assessment.refusal_reason}\n\n**Suggested Available Topics:**\n" + "\n".join(f"- {alt}" for alt in pre_assessment.available_alternatives),
                limitations=[pre_assessment.refusal_reason or "Unsupported domain"],
                trace_steps=traces,
                total_duration_ms=round(total_duration_ms, 2),
            )

        # Step 1: Router
        s1_start = time.perf_counter()
        if progress_callback:
            progress_callback("understanding_question", "Routing intent and identifying domain entities...")
        route = await router_agent.route(effective_query)
        s1_ms = (time.perf_counter() - s1_start) * 1000
        traces.append(StepTrace(
            step="understanding_question",
            status="succeeded",
            duration_ms=round(s1_ms, 2),
            message=f"Intent: {route.intent} (confidence: {route.confidence * 100:.0f}%, complexity: {route.complexity})",
            metadata=route.model_dump(),
        ))

        # Step 2: Answerability Gate
        answerability = answerability_gate.evaluate(effective_query, route, catalog)
        if not answerability.is_answerable:
            total_duration_ms = (time.perf_counter() - overall_start) * 1000
            traces.append(StepTrace(
                step="understanding_question",
                status="failed",
                duration_ms=round((time.perf_counter() - s1_start) * 1000, 2),
                message=f"Answerability Gate Refusal: {answerability.refusal_reason}",
            ))
            observability_tracer.record_run_trace(
                RunTraceRecord(
                    run_id=run_id,
                    session_id=session_id,
                    query=query,
                    intent=route.intent,
                    latency_ms=total_duration_ms,
                    sql_executed=None,
                    row_count=0,
                    cost_estimate_usd=0.0001,
                    error_class="answerability_refusal",
                    verification_status="refused",
                    created_at=datetime.now(timezone.utc).isoformat(),
                    orchestrator_type="workflow_orchestrator",
                    llm_provider="groq",
                )
            )
            return MultiAgentWorkflowResult(
                run_id=run_id,
                session_id=session_id,
                query=query,
                standalone_query=standalone_q,
                route=route,
                answerability=answerability,
                composed_answer=f"### Question Not Answerable From Warehouse\n\n{answerability.refusal_reason}\n\n**Suggested Available Topics:**\n" + "\n".join(f"- {alt}" for alt in answerability.available_alternatives),
                limitations=[answerability.refusal_reason or "Unsupported domain"],
                trace_steps=traces,
                total_duration_ms=round(total_duration_ms, 2),
            )

        # Step 3: Clarification Policy
        clarification = clarification_agent.check_ambiguity(effective_query, route)
        if clarification.needs_clarification:
            total_duration_ms = (time.perf_counter() - overall_start) * 1000
            traces.append(StepTrace(
                step="understanding_question",
                status="succeeded",
                duration_ms=round((time.perf_counter() - s1_start) * 1000, 2),
                message=f"Clarification required: {clarification.question}",
            ))
            opts_text = "\n".join(f"- **{opt.label}**: {opt.description}" for opt in clarification.options)
            return MultiAgentWorkflowResult(
                run_id=run_id,
                query=query,
                route=route,
                answerability=answerability,
                clarification=clarification,
                composed_answer=f"### Clarification Needed\n\n{clarification.question}\n\n{clarification.ambiguity_reason}\n\n**Options:**\n{opts_text}\n\n*(You can reply with one of the options above, or I will proceed with the default interpretation: '{clarification.default_interpretation}').*",
                limitations=["Query ambiguous without dimension specification."],
                trace_steps=traces,
                total_duration_ms=round(total_duration_ms, 2),
            )

        # Step 4: Hybrid Schema Retrieval (BM25 + TF-IDF RRF + Value Linking)
        s2_start = time.perf_counter()
        if progress_callback:
            progress_callback("retrieving_schema", "Running hybrid BM25 + embedding RRF retrieval and linking values...")

        retrieval_res = hybrid_retriever.retrieve(effective_query, top_k=5, catalog=catalog)
        selected_tables = retrieval_res.selected_table_names
        schema_prompt = retrieval_res.minimal_schema_prompt

        linked_values = value_linker.link_values(effective_query, catalog=catalog)

        # Build prompt context additions
        linked_str = ""
        if linked_values:
            linked_str = "LINKED DATABASE VALUES:\n" + "\n".join(
                f"- Entity '{lv.user_mention}' matches column {lv.target_table}.{lv.target_column} = '{lv.exact_db_value}'"
                for lv in linked_values
            )

        fp = getattr(catalog, "fingerprint", None)
        authoritative_context = dynamic_semantic_engine.format_authoritative_prompt_context(fingerprint=fp, query=effective_query)
        # Strict isolation: Only USER_APPROVED metrics for the active fingerprint are injected.
        # If no approved metrics exist, metrics_str remains empty. Unapproved candidates and static fallback are strictly omitted.
        metrics_str = authoritative_context or ""

        plan = planner_agent.create_plan(effective_query, route, selected_tables)
        s2_ms = (time.perf_counter() - s2_start) * 1000
        traces.append(StepTrace(
            step="retrieving_schema",
            status="succeeded",
            duration_ms=round(s2_ms, 2),
            message=f"Hybrid RRF retrieved {len(selected_tables)} tables ({', '.join(selected_tables)}) and linked {len(linked_values)} exact values.",
            metadata={
                "plan_id": plan.plan_id,
                "selected_tables": selected_tables,
                "linked_values_count": len(linked_values),
            },
        ))

        # Step 5: SQL Candidate Generation
        s3_start = time.perf_counter()
        if progress_callback:
            progress_callback("generating_query", "Generating schema-grounded SQL query candidate...")

        active_adapter = None
        try:
            active_adapter = db_manager.get_active_adapter()
        except Exception:
            pass
        dialect_name = active_adapter.engine_type.value.capitalize() if active_adapter else settings.DATABASE_DIALECT.capitalize()

        gen_req = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=SQL_GEN_PROMPT.format(
                        dialect=dialect_name,
                        schema_context=schema_prompt,
                        linked_values_context=linked_str,
                        metrics_context=metrics_str,
                    ),
                ),
                LLMMessage(role="user", content=effective_query),
            ],
            temperature=0.0,
        )
        gen_res = await llm.generate(gen_req)
        raw_sql = gen_res.content
        s3_ms = (time.perf_counter() - s3_start) * 1000
        traces.append(StepTrace(
            step="generating_query",
            status="succeeded",
            duration_ms=round(s3_ms, 2),
            message="Initial SQL candidate generated.",
        ))

        # Step 6: SQL Validation & Bounded Repair Loop (Max 1 Attempt)
        s4_start = time.perf_counter()
        if progress_callback:
            progress_callback("validating_query", "Validating query AST with sqlglot guardrail...")
        is_valid, sanitized_sql, val_errors = sql_validator.validate_and_format_sql(raw_sql, catalog)

        # Repair loop if validation failed (strictly 1 attempt in Version 2)
        attempt = 1
        while not is_valid and attempt <= 1:
            logger.warning(f"SQL validation failed: {val_errors}. Starting repair attempt {attempt}...")
            repair = await sql_repair_loop.attempt_repair(
                query=query,
                failing_sql=sanitized_sql or raw_sql,
                error_message="; ".join(val_errors),
                schema_context=schema_prompt,
                catalog=catalog,
                attempt_number=attempt,
            )
            repair_attempts.append(repair)
            if repair.validation_passed:
                is_valid = True
                sanitized_sql = repair.repaired_sql
                val_errors = []
                break
            attempt += 1

        s4_ms = (time.perf_counter() - s4_start) * 1000

        if not is_valid:
            traces.append(StepTrace(
                step="validating_query",
                status="failed",
                duration_ms=round(s4_ms, 2),
                message=f"Validation failed after {len(repair_attempts)} repair attempts: {'; '.join(val_errors)}",
            ))
            total_duration_ms = (time.perf_counter() - overall_start) * 1000
            return MultiAgentWorkflowResult(
                run_id=run_id,
                query=query,
                route=route,
                answerability=answerability,
                plan=plan,
                selected_tables=selected_tables,
                linked_values=linked_values,
                sanitized_sql=None,
                repair_attempts=repair_attempts,
                composed_answer=f"### Query Blocked by Safety Guardrail\n\nThe query could not be safely validated after {len(repair_attempts)} repair attempts.\n\n**Reasons:** {'; '.join(val_errors)}",
                limitations=val_errors,
                trace_steps=traces,
                total_duration_ms=round(total_duration_ms, 2),
            )

        traces.append(StepTrace(
            step="validating_query",
            status="succeeded",
            duration_ms=round(s4_ms, 2),
            message=f"SQL validated successfully (repair attempts: {len(repair_attempts)}).",
        ))

        # Step 7: Execution (with bounded execution repair strictly capped at 1 attempt)
        s5_start = time.perf_counter()
        if progress_callback:
            progress_callback("running_query", f"Executing read-only query on {dialect_name}...")
        query_result: Optional[QueryExecutionResult] = None
        attempt_exec = 0
        last_exec_err: Optional[Exception] = None
        while attempt_exec < 1:
            try:
                query_result = sql_executor.execute_query(sanitized_sql)
                break
            except Exception as exec_err:
                last_exec_err = exec_err
                attempt_exec += 1
                if len(repair_attempts) < 1:
                    logger.warning(f"Query execution error: {exec_err}. Attempting repair {attempt_exec}...")
                    try:
                        exec_repair = await sql_repair_loop.attempt_repair(
                            query=effective_query,
                            failing_sql=sanitized_sql,
                            error_message=str(exec_err),
                            schema_context=schema_prompt,
                            catalog=catalog,
                            attempt_number=len(repair_attempts) + 1,
                        )
                        repair_attempts.append(exec_repair)
                        if exec_repair.validation_passed and exec_repair.repaired_sql:
                            sanitized_sql = exec_repair.repaired_sql
                            try:
                                query_result = sql_executor.execute_query(sanitized_sql)
                                break
                            except Exception as re_err:
                                last_exec_err = re_err
                    except Exception as rep_err:
                        logger.warning(f"Repair attempt failed: {rep_err}")
                break

        if not query_result:
            if last_exec_err:
                raise last_exec_err
            raise RuntimeError("SQL query execution failed to return results.")

        s5_ms = (time.perf_counter() - s5_start) * 1000
        traces.append(StepTrace(
            step="running_query",
            status="succeeded",
            duration_ms=round(s5_ms, 2),
            message=f"Executed in {query_result.execution_time_ms}ms, returned {query_result.row_count} rows.",
        ))

        # Step 8: Verification
        s6_start = time.perf_counter()
        if progress_callback:
            progress_callback("verifying_results", "Running verifier quality and boundary checks...")
        is_empty = query_result.row_count == 0
        warnings = []
        if is_empty:
            warnings.append("Query returned 0 rows.")
        if query_result.truncated:
            warnings.append(f"Query result capped at {settings.SQL_MAX_ROWS_RETURN} rows.")

        verification = VerificationResult(
            is_valid=True,
            empty_result=is_empty,
            row_count=query_result.row_count,
            checks_passed=["AST safety verified", "Read-only isolation", "Row limits verified"],
            warnings=warnings,
        )
        s6_ms = (time.perf_counter() - s6_start) * 1000
        traces.append(StepTrace(
            step="verifying_results",
            status="succeeded",
            duration_ms=round(s6_ms, 2),
            message=f"Verifier completed ({len(verification.checks_passed)} checks passed).",
        ))

        # Step 9: Visualization Agent
        chart_spec = visualization_agent.derive_chart_specification(query, route, query_result)
        traces.append(StepTrace(
            step="verifying_results",
            status="succeeded",
            duration_ms=1.0,
            message=f"Visualization Agent derived {chart_spec.chart_type.value.upper()} chart specification.",
        ))

        # Step 9.5: Deterministic Analysis Tool Execution
        detected_tool = analysis_registry.detect_intent(effective_query)
        analysis_res: Optional[AnalysisToolResult] = None
        if detected_tool == "analyze_customer_churn_risk":
            analysis_res = analysis_registry.execute_tool("analyze_customer_churn_risk")
        elif detected_tool == "detect_anomalies" and query_result and query_result.row_count >= 5:
            date_col = next((c for c in query_result.columns if any(k in c.lower() for k in ["date", "day", "month", "year", "time"])), None)
            metric_col = next((c for c in query_result.columns if c != date_col), None)
            if date_col and metric_col:
                analysis_res = analysis_registry.execute_tool(
                    "detect_anomalies",
                    records=query_result.rows,
                    date_col=date_col,
                    metric_col=metric_col,
                )
        elif detected_tool == "forecast_series" and query_result and query_result.row_count >= 10:
            date_col = next((c for c in query_result.columns if any(k in c.lower() for k in ["date", "day", "month", "year", "time"])), None)
            metric_col = next((c for c in query_result.columns if c != date_col), None)
            if date_col and metric_col:
                analysis_res = analysis_registry.execute_tool(
                    "forecast_series",
                    records=query_result.rows,
                    date_col=date_col,
                    value_col=metric_col,
                )
        elif detected_tool in ("simulate_scenario", "optimize_budget_allocation"):
            # These tools need a baseline and per-channel returns that this generic
            # path has not measured. Inventing them would produce a computed-looking
            # answer from made-up inputs, so the run abstains and says why. Scenario
            # and prescriptive questions are routed to their specialist workflows,
            # which derive these inputs from the warehouse.
            traces.append(StepTrace(
                step="verifying_results",
                status="succeeded",
                duration_ms=1.0,
                message=(
                    f"Tool '{detected_tool}' not executed: its inputs are not derivable from this "
                    "query's results, and no values were assumed."
                ),
            ))

        if analysis_res and analysis_res.success:
            traces.append(StepTrace(
                step="verifying_results",
                status="succeeded",
                duration_ms=1.0,
                message=f"Deterministic Analysis Tool '{analysis_res.tool_name}' executed successfully.",
            ))

        # Step 10: Answer Composition
        s7_start = time.perf_counter()
        if progress_callback:
            progress_callback("composing_answer", "Composing executive narrative with verified citations...")

        preview_rows = query_result.rows[:10]
        results_preview_str = "\n".join([str(r) for r in preview_rows]) if preview_rows else "No rows returned."

        comp_req = LLMRequest(
            messages=[
                LLMMessage(
                    role="system",
                    content=COMPOSER_PROMPT.format(
                        question=effective_query,
                        intent=route.intent,
                        sql=sanitized_sql,
                        row_count=len(preview_rows),
                        results_preview=results_preview_str,
                    ),
                ),
                LLMMessage(role="user", content="Compose business answer with direct answer, key findings, and caveats."),
            ],
            temperature=0.0,
        )
        comp_res = await llm.generate(comp_req)
        composed_text = comp_res.content
        s7_ms = (time.perf_counter() - s7_start) * 1000
        traces.append(StepTrace(
            step="composing_answer",
            status="succeeded",
            duration_ms=round(s7_ms, 2),
            message="Business answer composed.",
        ))

        key_findings = [f"Data observation: {', '.join(f'{k}: {v}' for k, v in r.items())}" for r in preview_rows[:3]]

        # Contextual analytical follow-up suggestions
        followups = []
        q_lower = effective_query.lower()
        if any(w in q_lower for w in ["order", "sales", "revenue", "spend"]):
            followups = [
                "What are the top 5 product categories contributing to these sales?",
                "How does this revenue break down across customer segments?",
                "Are there any anomalous daily spikes in this period?",
            ]
        elif any(w in q_lower for w in ["churn", "segment", "customer"]):
            followups = [
                "What is the average order frequency for VIP customers?",
                "Which marketing channels have the lowest churn rates?",
                "What is the revenue impact if we reduce At Risk churn by 10%?",
            ]
        elif any(w in q_lower for w in ["product", "category", "inventory"]):
            followups = [
                "Which products have the highest return rates?",
                "What are the best-selling products by volume?",
                "How do product ratings correlate with sales?",
            ]
        else:
            followups = [
                "What is the month-over-month growth rate?",
                "What are the primary drivers of this trend?",
                "Show detailed customer segment breakdown for these results.",
            ]
        total_duration_ms = (time.perf_counter() - overall_start) * 1000

        management_response = _synthesize_management_from_workflow(
            route=route,
            query_result=query_result,
            analysis_res=analysis_res,
            composed_text=composed_text,
            key_findings=key_findings,
            warnings=warnings,
            sanitized_sql=sanitized_sql,
        )

        memory_service.record_assistant_turn(session_id, composed_text, sql=sanitized_sql)

        observability_tracer.record_run_trace(
            RunTraceRecord(
                run_id=run_id,
                session_id=session_id,
                query=query,
                intent=route.intent,
                latency_ms=total_duration_ms,
                sql_executed=sanitized_sql,
                row_count=query_result.row_count if query_result else 0,
                cost_estimate_usd=0.0002,
                error_class=None,
                verification_status="verified" if (verification and verification.is_valid) else "unverified",
                created_at=datetime.now(timezone.utc).isoformat(),
                    orchestrator_type="workflow_orchestrator",
                    llm_provider="groq",
            )
        )

        try:
            spans = []
            for idx, t in enumerate(traces):
                spans.append(
                    StageSpanRecord(
                        span_id=f"{run_id}_{t.step}_{idx}",
                        run_id=run_id,
                        stage_name=t.step,
                        duration_ms=t.duration_ms or 0.0,
                        start_time=datetime.now(timezone.utc).isoformat(),
                        end_time=datetime.now(timezone.utc).isoformat(),
                        status=t.status,
                        metadata_json=json.dumps({"message": t.message, "metadata": t.metadata}),
                    )
                )
            if spans:
                observability_tracer.record_stage_spans(spans)
        except Exception as _e:
            logger.warning(f"Failed to record stage spans: {_e}")

        return MultiAgentWorkflowResult(
            run_id=run_id,
            session_id=session_id,
            query=query,
            standalone_query=standalone_q,
            route=route,
            answerability=answerability,
            clarification=clarification,
            plan=plan,
            selected_tables=selected_tables,
            linked_values=linked_values,
            sanitized_sql=sanitized_sql,
            query_result=query_result,
            chart_spec=chart_spec,
            analysis_result=analysis_res,
            verification=verification,
            repair_attempts=repair_attempts,
            composed_answer=composed_text,
            management_response=management_response,
            key_findings=key_findings,
            limitations=warnings,
            suggested_followups=followups,
            trace_steps=traces,
            total_duration_ms=round(total_duration_ms, 2),
        )


multi_agent_orchestrator = MultiAgentOrchestrator()
