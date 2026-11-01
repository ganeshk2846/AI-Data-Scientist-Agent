"""
SQL AST Validator and Security Guardrail using sqlglot.
Enforces read-only SELECT statements, allowlisted schema identifiers, and row limits.
"""

import re
from typing import List, Tuple
import sqlglot
from sqlglot import exp
from backend.app.core.config import settings
from backend.app.core.errors import ValidationError
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service

DISALLOWED_EXPRESSIONS = (
    exp.Insert,
    exp.Update,
    exp.Delete,
    exp.Create,
    exp.Drop,
    exp.Alter,
    exp.Command,
    exp.Pragma,
)


class SQLValidator:
    """Validates generated SQL for security, schema conformance, and read-only guarantees."""

    def __init__(self):
        pass

    def validate_and_format_sql(self, sql_query: str, catalog: DatabaseCatalog) -> Tuple[bool, str, List[str]]:
        """
        Parses SQL AST using sqlglot.
        Returns: (is_valid, sanitized_sql, error_messages)
        """
        cleaned_sql = sql_query.strip()
        # Strip markdown fences if present
        if cleaned_sql.startswith("```"):
            cleaned_sql = re.sub(r"^```(?:sql)?\s*", "", cleaned_sql, flags=re.IGNORECASE)
            cleaned_sql = re.sub(r"\s*```$", "", cleaned_sql)
            cleaned_sql = cleaned_sql.strip()

        # Reject multiple statements (check for unescaped semicolon followed by non-whitespace)
        statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
        if len(statements) > 1:
            return False, cleaned_sql, ["Multiple statement execution is blocked for security."]

        single_stmt = statements[0] if statements else ""
        if not single_stmt:
            return False, "", ["Empty SQL query provided."]

        # Disallow unsafe keywords
        upper = single_stmt.upper()
        for forbidden in ["ATTACH", "DETACH", "PRAGMA", "LOAD_EXTENSION", "VACUUM", "REINDEX"]:
            if re.search(r"\b" + forbidden + r"\b", upper):
                return False, single_stmt, [f"Disallowed command or statement type: {forbidden}"]

        # AST Parse with sqlglot
        try:
            expression = sqlglot.parse_one(single_stmt, read="sqlite")
        except Exception as e:
            return False, single_stmt, [f"SQL syntax parse error: {str(e)}"]

        # Check expression type: must be Select or Union of Selects
        if not isinstance(expression, (exp.Select, exp.Union)):
            return False, single_stmt, [
                f"Only read-only SELECT statements are permitted. Received: {expression.key.upper()}"
            ]

        # Check for any disallowed sub-expressions (e.g. within CTEs)
        for disallowed in DISALLOWED_EXPRESSIONS:
            if expression.find(disallowed):
                return False, single_stmt, [
                    f"Query contains forbidden modification clause: {disallowed.__name__}"
                ]

        # Verify referenced table identifiers exist in real schema
        catalog_table_names = {k.lower(): k for k in catalog.tables.keys()}
        referenced_tables = [t.name.lower() for t in expression.find_all(exp.Table)]

        for ref_t in referenced_tables:
            # Ignore CTE alias references
            ctes = [cte.alias.lower() for cte in expression.find_all(exp.CTE) if cte.alias]
            if ref_t in ctes:
                continue

            if ref_t not in catalog_table_names:
                return False, single_stmt, [
                    f"Schema validation error: Table '{ref_t}' does not exist in the connected database."
                ]

        # Enforce row limit
        limit_expr = expression.find(exp.Limit)
        if not limit_expr:
            expression = expression.limit(settings.SQL_MAX_ROWS_RETURN)
        else:
            # If user limit exceeds max allowable rows, cap it
            try:
                user_limit = int(limit_expr.expression.this)
                if user_limit > settings.SQL_MAX_ROWS_RETURN:
                    expression = expression.limit(settings.SQL_MAX_ROWS_RETURN)
            except Exception:
                pass

        sanitized_sql = expression.sql(dialect="sqlite")
        return True, sanitized_sql, []


sql_validator = SQLValidator()

