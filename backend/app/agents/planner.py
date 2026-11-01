"""
Planner Agent.
Decomposes complex questions into an inspectable, typed Execution Plan DAG.
"""

import uuid
from typing import List, Optional
from backend.app.agents.contracts import ExecutionPlan, PlanStep
from backend.app.agents.router import RouteResult


class PlannerAgent:
    """Builds typed execution DAGs with step dependencies and tools."""

    def create_plan(self, query: str, route: RouteResult, selected_tables: List[str]) -> ExecutionPlan:
        plan_id = str(uuid.uuid4())

        steps = [
            PlanStep(
                step_id="step_1_grounding",
                tool_name="schema_grounder",
                description="Ground query into schema catalog and select relevant tables",
                dependencies=[],
                arguments={"query": query, "tables": selected_tables},
            ),
            PlanStep(
                step_id="step_2_sql_generation",
                tool_name="sql_generator",
                description="Synthesize schema-grounded SQLite SELECT statement",
                dependencies=["step_1_grounding"],
                arguments={"tables": selected_tables},
            ),
            PlanStep(
                step_id="step_3_sql_validation",
                tool_name="sql_validator",
                description="Parse AST via sqlglot, enforce read-only policy, verify identifiers",
                dependencies=["step_2_sql_generation"],
                arguments={"dialect": "sqlite", "max_rows": 1000},
            ),
            PlanStep(
                step_id="step_4_sql_execution",
                tool_name="sql_executor",
                description="Execute validated query on ecommerce.sqlite (mode=ro)",
                dependencies=["step_3_sql_validation"],
                arguments={"timeout_seconds": 30},
            ),
            PlanStep(
                step_id="step_5_verification",
                tool_name="result_verifier",
                description="Verify non-empty results, boundary checks, and arithmetic sanity",
                dependencies=["step_4_sql_execution"],
                arguments={},
            ),
            PlanStep(
                step_id="step_6_visualization",
                tool_name="visualization_agent",
                description="Derive typed chart specification (bar, line, or table fallback)",
                dependencies=["step_5_verification"],
                arguments={"intent": route.intent},
            ),
            PlanStep(
                step_id="step_7_composition",
                tool_name="composer",
                description="Compose executive narrative with evidence citations and limitations",
                dependencies=["step_5_verification", "step_6_visualization"],
                arguments={},
            ),
        ]

        return ExecutionPlan(
            plan_id=plan_id,
            goal=f"Answer '{query}' via grounded SQL analysis and verifiable evidence.",
            steps=steps,
            current_step_id="step_1_grounding",
        )


planner_agent = PlannerAgent()
