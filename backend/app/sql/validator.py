"""
backend/app/sql/validator.py
SQL AST Validator and Security Guardrail using sqlglot.
Enforces read-only SELECT statements, allowlisted schema identifiers, column existence, and row limits.
Dialect-aware across SQLite, PostgreSQL, and MySQL.
"""

import re
from typing import List, Optional, Tuple
import sqlglot
from sqlglot import exp
from backend.app.core.config import settings
from backend.app.core.contracts import SupportedEngine
from backend.app.db.manager import db_manager
from backend.app.schema.models import DatabaseCatalog

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

FORBIDDEN_KEYWORDS = [
    "ATTACH", "DETACH", "PRAGMA", "LOAD_EXTENSION", "VACUUM", "REINDEX",
    "COPY", "LOAD DATA", "OUTFILE", "DUMPFILE", "PG_READ_FILE", "DBLINK"
]


class SQLValidator:
    """Validates generated SQL for security, schema conformance, dialect compatibility, and read-only guarantees."""

    def __init__(self):
        pass

    def _resolve_dialect(self, dialect: Optional[str] = None) -> str:
        """Determines target sqlglot dialect name."""
        if dialect:
            return dialect
        try:
            adapter = db_manager.get_active_adapter()
            if adapter.engine_type == SupportedEngine.POSTGRESQL:
                return "postgres"
            elif adapter.engine_type == SupportedEngine.MYSQL:
                return "mysql"
            return "sqlite"
        except Exception:
            return "sqlite"

    def validate_and_format_sql(
        self,
        sql_query: str,
        catalog: DatabaseCatalog,
        dialect: Optional[str] = None,
    ) -> Tuple[bool, str, List[str]]:
        """
        Parses SQL AST using sqlglot with dialect awareness.
        Returns: (is_valid, sanitized_sql, error_messages)
        """
        target_dialect = self._resolve_dialect(dialect)
        cleaned_sql = sql_query.strip()

        # Strip thinking tags if present (<think>...</think>)
        cleaned_sql = re.sub(r"<think>.*?</think>", "", cleaned_sql, flags=re.DOTALL).strip()

        # Extract SQL from markdown code fences if present anywhere in text
        code_fence_match = re.search(r"```(?:sql)?\s*(.*?)\s*```", cleaned_sql, flags=re.DOTALL | re.IGNORECASE)
        if code_fence_match:
            cleaned_sql = code_fence_match.group(1).strip()
        else:
            # Strip leading/trailing fences if only partially matched
            cleaned_sql = re.sub(r"^```(?:sql)?\s*", "", cleaned_sql, flags=re.IGNORECASE)
            cleaned_sql = re.sub(r"\s*```$", "", cleaned_sql)
            cleaned_sql = cleaned_sql.strip()

        # Reject multiple statements
        statements = [s.strip() for s in cleaned_sql.split(";") if s.strip()]
        if len(statements) > 1:
            return False, cleaned_sql, ["Multiple statement execution is blocked for security."]

        single_stmt = statements[0] if statements else ""
        if not single_stmt:
            return False, "", ["Empty SQL query provided."]

        # Disallow unsafe keywords
        upper = single_stmt.upper()
        for forbidden in FORBIDDEN_KEYWORDS:
            if re.search(r"\b" + forbidden + r"\b", upper):
                return False, single_stmt, [f"Disallowed command or statement type: {forbidden}"]

        # AST Parse with sqlglot
        try:
            expression = sqlglot.parse_one(single_stmt, read=target_dialect)
        except Exception as e:
            return False, single_stmt, [f"SQL syntax parse error for dialect '{target_dialect}': {str(e)}"]

        # Check expression type: must be Select or Union of Selects
        if not isinstance(expression, (exp.Select, exp.Union)):
            return False, single_stmt, [
                f"Only read-only SELECT statements are permitted. Received: {expression.key.upper()}"
            ]

        # Check for any disallowed modification sub-expressions (e.g. inside CTEs)
        for disallowed in DISALLOWED_EXPRESSIONS:
            if expression.find(disallowed):
                return False, single_stmt, [
                    f"Query contains forbidden modification clause: {disallowed.__name__}"
                ]

        # Verify referenced table identifiers exist in real catalog schema
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

        # Verify referenced column identifiers against single-table queries
        # (For simple queries referencing one table, verify all columns exist in that table)
        if len(referenced_tables) == 1 and referenced_tables[0] in catalog_table_names:
            target_table_name = catalog_table_names[referenced_tables[0]]
            target_table_model = catalog.tables[target_table_name]
            allowed_cols = {c.name.lower() for c in target_table_model.columns}
            # Collect SELECT aliases so they are not rejected in GROUP BY / ORDER BY / HAVING
            select_aliases = {a.alias.lower() for a in expression.find_all(exp.Alias) if a.alias}

            for col_node in expression.find_all(exp.Column):
                col_name = col_node.name.lower()
                # Skip wildcard, empty, or SELECT alias references
                if col_name == "*" or not col_name or col_name in select_aliases:
                    continue
                if col_name not in allowed_cols:
                    return False, single_stmt, [
                        f"Schema validation error: Column '{col_node.name}' does not exist in table '{target_table_name}'."
                    ]

        # Enforce row limit
        limit_expr = expression.find(exp.Limit)
        if not limit_expr:
            expression = expression.limit(settings.SQL_MAX_ROWS_RETURN)
        else:
            try:
                user_limit = int(limit_expr.expression.this)
                if user_limit > settings.SQL_MAX_ROWS_RETURN:
                    expression = expression.limit(settings.SQL_MAX_ROWS_RETURN)
            except Exception:
                pass

        sanitized_sql = expression.sql(dialect=target_dialect)
        return True, sanitized_sql, []


sql_validator = SQLValidator()
