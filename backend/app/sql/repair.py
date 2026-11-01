"""
Bounded SQL Repair Loop.
Recovers from syntax, identifier, or execution errors with at most two bounded repair retries.
Validates each repaired query again from scratch before execution.
"""

import re
from typing import List, Optional, Tuple
from backend.app.agents.contracts import RepairAttempt
from backend.app.core.logging import logger
from backend.app.llm.client import get_llm_provider
from backend.app.llm.models import LLMMessage, LLMRequest
from backend.app.schema.models import DatabaseCatalog
from backend.app.sql.validator import sql_validator

REPAIR_SYSTEM_PROMPT = """You are an expert SQL Repair Engineer.
The previous SQLite query generated to answer the user's question encountered an error.
Using the exact error message and the verified database schema below, write a corrected SQLite SELECT query.

STRICT CONSTRAINTS:
1. Fix the specific error mentioned (e.g. invalid column name, misplaced clause, grouping syntax).
2. Use ONLY tables and columns that exist in the provided schema.
3. Output ONLY the corrected SQL query inside a markdown ```sql code block.

SCHEMA CONTEXT:
{schema_context}

FAILED QUERY:
{failed_sql}

ERROR MESSAGE:
{error_message}
"""


class SQLRepairLoop:
    """Manages at most two bounded automatic query repair attempts."""

    async def attempt_repair(
        self,
        query: str,
        failing_sql: str,
        error_message: str,
        schema_context: str,
        catalog: DatabaseCatalog,
        attempt_number: int,
    ) -> RepairAttempt:
        if attempt_number > 2:
            raise ValueError("Repair limit exceeded: maximum 2 repair retries permitted.")

        logger.info(f"Initiating SQL repair attempt {attempt_number}/2 for query: {failing_sql[:80]}...")
        llm = get_llm_provider()

        prompt = REPAIR_SYSTEM_PROMPT.format(
            schema_context=schema_context,
            failed_sql=failing_sql,
            error_message=error_message,
        )

        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content=prompt),
                LLMMessage(role="user", content=f"Fix the query for user question: {query}"),
            ],
            temperature=0.0,
        )
        res = await llm.generate(req)
        raw_repaired = res.content

        # Re-validate the repaired query from scratch via sqlglot
        is_valid, sanitized_repaired, val_errors = sql_validator.validate_and_format_sql(
            raw_repaired, catalog
        )

        explanation = f"Repair attempt {attempt_number}: Addressed '{error_message}'."
        if not is_valid:
            explanation += f" Repaired query failed validation: {'; '.join(val_errors)}"

        return RepairAttempt(
            attempt_number=attempt_number,
            original_sql=failing_sql,
            error_message=error_message,
            repaired_sql=sanitized_repaired if is_valid else raw_repaired,
            explanation=explanation,
            success=is_valid,
            validation_passed=is_valid,
        )


sql_repair_loop = SQLRepairLoop()

