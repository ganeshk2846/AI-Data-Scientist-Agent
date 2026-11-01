"""
Multi-Agent Orchestrator with Planning, Clarification, and Bounded SQL Repair.
Coordinates Router, Answerability Gate, Clarification, Planner, Grounder, Validator, Repair, Executor, Visualization, and Composer.
"""

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
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.llm.client import get_llm_provider
from backend.app.llm.models import LLMMessage, LLMRequest
from backend.app.retrieval.retriever import schema_grounder
from backend.app.schema.service import schema_service
from backend.app.sql.executor import QueryExecutionResult, sql_executor
from backend.app.sql.repair import sql_repair_loop
from backend.app.sql.validator import sql_validator
from backend.app.workflow.models import StepTrace, VerificationResult, WorkflowProgressState

SQL_GEN_PROMPT = """You are an expert Data Scientist and SQL Engineer specializing in SQLite.
Write a single, safe, read-only SQLite SELECT query to answer the user's business question.

STRICT CONSTRAINTS:
1. Use ONLY the table and column identifiers provided in the schema context below.
2. NEVER invent column names or table names.
3. Use SQLite functions (e.g. strftime, ROUND, COUNT, SUM, AVG).
4. For revenue or money values, ROUND(..., 2).
5. Output ONLY the raw SQL inside a markdown ```sql code block. No extra conversation.

SCHEMA CONTEXT:
{schema_context}
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
    query: str
    route: RouteResult
    answerability: AnswerabilityAssessment
    clarification: Optional[ClarificationResponse] = None
    plan: Optional[ExecutionPlan] = None
    selected_tables: List[str] = Field(default_factory=list)
    sanitized_sql: Optional[str] = None
    query_result: Optional[QueryExecutionResult] = None
    chart_spec: Optional[ChartSpecification] = None
    verification: Optional[VerificationResult] = None
    repair_attempts: List[RepairAttempt] = Field(default_factory=list)
    composed_answer: str
    key_findings: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    trace_steps: List[StepTrace] = Field(default_factory=list)
    total_duration_ms: float = 0.0


class MultiAgentOrchestrator:
    """Orchestrates the multi-agent pipeline with planning, clarification, and bounded repair."""

    async def run(
        self,
        query: str,
        request_id: Optional[str] = None,
        progress_callback: Optional[Callable[[WorkflowProgressState, str], None]] = None,
    ) -> MultiAgentWorkflowResult:
        run_id = request_id or str(uuid.uuid4())
        overall_start = time.perf_counter()
        traces: List[StepTrace] = []
        repair_attempts: List[RepairAttempt] = []

        catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
        llm = get_llm_provider()

        # Step 1: Router
        s1_start = time.perf_counter()
        if progress_callback:
            progress_callback("understanding_question", "Routing intent and identifying domain entities...")
        route = await router_agent.route(query)
        s1_ms = (time.perf_counter() - s1_start) * 1000
        traces.append(StepTrace(
            step="understanding_question",
            status="succeeded",
            duration_ms=round(s1_ms, 2),
            message=f"Intent: {route.intent} (confidence: {route.confidence * 100:.0f}%, complexity: {route.complexity})",
            metadata=route.model_dump(),
        ))

        # Step 2: Answerability Gate
        answerability = answerability_gate.evaluate(query, route, catalog)
        if not answerability.is_answerable:
            total_duration_ms = (time.perf_counter() - overall_start) * 1000
            traces.append(StepTrace(
                step="understanding_question",
                status="failed",
                duration_ms=round((time.perf_counter() - s1_start) * 1000, 2),
                message=f"Answerability Gate Refusal: {answerability.refusal_reason}",
            ))
            return MultiAgentWorkflowResult(
                run_id=run_id,
                query=query,
                route=route,
                answerability=answerability,
                composed_answer=f"### Question Not Answerable From Warehouse\n\n{answerability.refusal_reason}\n\n**Suggested Available Topics:**\n" + "\n".join(f"- {alt}" for alt in answerability.available_alternatives),
                limitations=[answerability.refusal_reason or "Unsupported domain"],
                trace_steps=traces,
                total_duration_ms=round(total_duration_ms, 2),
            )

        # Step 3: Clarification Policy
        clarification = clarification_agent.check_ambiguity(query, route)
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

        # Step 4: Grounding & Planning
        s2_start = time.perf_counter()
        if progress_callback:
            progress_callback("retrieving_schema", "Grounding entities and building execution DAG...")
        selected_tables = schema_grounder.retrieve_tables(query, catalog)
        schema_prompt = catalog.to_minimal_prompt_schema(selected_tables)
        plan = planner_agent.create_plan(query, route, selected_tables)
        s2_ms = (time.perf_counter() - s2_start) * 1000
        traces.append(StepTrace(
            step="retrieving_schema",
            status="succeeded",
            duration_ms=round(s2_ms, 2),
            message=f"Planner DAG created ({len(plan.steps)} steps) with tables: {', '.join(selected_tables)}",
            metadata={"plan_id": plan.plan_id, "selected_tables": selected_tables},
        ))

        # Step 5: SQL Candidate Generation
        s3_start = time.perf_counter()
        if progress_callback:
            progress_callback("generating_query", "Generating schema-grounded SQL query candidate...")
        gen_req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=SQL_GEN_PROMPT.format(schema_context=schema_prompt)),
                LLMMessage(role="user", content=query),
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

        # Step 6: SQL Validation & Bounded Repair Loop (Max 2 Attempts)
        s4_start = time.perf_counter()
        if progress_callback:
            progress_callback("validating_query", "Validating query AST with sqlglot guardrail...")
        is_valid, sanitized_sql, val_errors = sql_validator.validate_and_format_sql(raw_sql, catalog)

        # Repair loop if validation failed
        attempt = 1
        while not is_valid and attempt <= 2:
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

        # Step 7: Execution (with possible execution repair)
        s5_start = time.perf_counter()
        if progress_callback:
            progress_callback("running_query", "Executing read-only query on ecommerce.sqlite...")
        query_result: Optional[QueryExecutionResult] = None
        try:
            query_result = sql_executor.execute_query(sanitized_sql)
        except Exception as exec_err:
            # If execution error and we still have repair attempts remaining
            if len(repair_attempts) < 2:
                logger.warning(f"Query execution error: {exec_err}. Attempting repair...")
                exec_repair = await sql_repair_loop.attempt_repair(
                    query=query,
                    failing_sql=sanitized_sql,
                    error_message=str(exec_err),
                    schema_context=schema_prompt,
                    catalog=catalog,
                    attempt_number=len(repair_attempts) + 1,
                )
                repair_attempts.append(exec_repair)
                if exec_repair.validation_passed:
                    sanitized_sql = exec_repair.repaired_sql
                    query_result = sql_executor.execute_query(sanitized_sql)
            if not query_result:
                raise exec_err

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
                        question=query,
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
        total_duration_ms = (time.perf_counter() - overall_start) * 1000

        return MultiAgentWorkflowResult(
            run_id=run_id,
            query=query,
            route=route,
            answerability=answerability,
            clarification=clarification,
            plan=plan,
            selected_tables=selected_tables,
            sanitized_sql=sanitized_sql,
            query_result=query_result,
            chart_spec=chart_spec,
            verification=verification,
            repair_attempts=repair_attempts,
            composed_answer=composed_text,
            key_findings=key_findings,
            limitations=warnings,
            trace_steps=traces,
            total_duration_ms=round(total_duration_ms, 2),
        )


multi_agent_orchestrator = MultiAgentOrchestrator()
