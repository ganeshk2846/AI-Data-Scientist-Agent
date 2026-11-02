"""
backend/app/analysis/data_extractor.py
Schema-Grounded, Multi-Engine Analytical Data Extraction Layer.
Safely extracts records and aggregates from active database adapters (SQLite, PostgreSQL, MySQL)
using read-only AST-validated SQL execution.
"""

from typing import Any, Dict, List, Optional, Tuple
import pandas as pd

from backend.app.analysis.contracts_v2 import AnalyticalPlan
from backend.app.core.errors import DatabaseReadOnlyViolationError
from backend.app.core.logging import logger
from backend.app.db.manager import db_manager
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service
from backend.app.sql.executor import SQLExecutor, sql_executor
from backend.app.sql.validator import sql_validator


class AnalyticalDataExtractor:
    """
    Extracts tabular datasets for statistical and machine-learning analysis.
    Grounds extractions strictly in the active database connection.
    """

    def __init__(self, executor: Optional[SQLExecutor] = None):
        self.executor = executor or sql_executor

    def extract_data_for_plan(
        self,
        plan: AnalyticalPlan,
        catalog: Optional[DatabaseCatalog] = None,
        custom_sql: Optional[str] = None,
    ) -> Tuple[bool, Optional[pd.DataFrame], List[str], Optional[str]]:
        """
        Executes grounded SQL data extraction for the given analytical plan.
        Returns: (success, dataframe, executed_queries, error_or_abstain_reason)
        """
        cat = catalog or schema_service.get_cached_catalog()
        if not cat:
            return False, None, [], "Active database catalog not available for extraction."

        # Determine SQL to execute
        sql_to_run = custom_sql or plan.data_extraction_sql

        if not sql_to_run:
            # Generate deterministic extraction query from plan schema bindings
            sql_to_run = self._synthesize_extraction_sql(plan, cat)

        if not sql_to_run:
            return False, None, [], f"Could not synthesize extraction query for plan {plan.plan_id}."

        # AST Validation & Read-Only Policy Check
        is_valid, sanitized_sql, val_errors = sql_validator.validate_and_format_sql(sql_to_run, cat)
        if not is_valid:
            logger.warning(f"Analytical extraction SQL failed validation: {val_errors}")
            return False, None, [], f"Extraction query rejected by security guardrails: {'; '.join(val_errors)}"

        try:
            exec_res = self.executor.execute_query(sanitized_sql)
            if exec_res.error:
                return False, None, [sanitized_sql], f"Database execution error: {exec_res.error}"

            records = exec_res.rows
            if not records:
                return False, pd.DataFrame(), [sanitized_sql], "Query executed successfully but returned 0 rows."

            df = pd.DataFrame(records)
            return True, df, [sanitized_sql], None

        except DatabaseReadOnlyViolationError as ro_err:
            logger.error(f"Read-only violation during analytical extraction: {ro_err}")
            return False, None, [sanitized_sql], f"Read-only violation: {ro_err}"
        except Exception as e:
            logger.error(f"Error during analytical extraction: {e}")
            return False, None, [sanitized_sql], f"Extraction error: {str(e)}"

    def _synthesize_extraction_sql(self, plan: AnalyticalPlan, catalog: DatabaseCatalog) -> Optional[str]:
        """
        Synthesizes a minimal, clean, read-only SELECT query grounded in plan tables and columns.
        """
        if not plan.relevant_tables:
            return None

        primary_table = plan.relevant_tables[0]
        if plan.target_variable and "." in plan.target_variable:
            tgt_tbl = plan.target_variable.split(".")[0]
            if tgt_tbl in catalog.tables:
                primary_table = tgt_tbl
        elif plan.time_dimension and "." in plan.time_dimension:
            time_tbl = plan.time_dimension.split(".")[0]
            if time_tbl in catalog.tables:
                primary_table = time_tbl

        tbl_model = catalog.tables.get(primary_table)
        if not tbl_model:
            return None

        existing_col_names = {c.name for c in tbl_model.columns}

        # Build columns to select
        cols = []
        time_col_in_tbl = None
        if plan.time_dimension:
            t_col = plan.time_dimension.split(".")[-1]
            if t_col in existing_col_names:
                cols.append(t_col)
                time_col_in_tbl = t_col

        if plan.target_variable:
            v_col = plan.target_variable.split(".")[-1]
            if v_col in existing_col_names and v_col not in cols:
                cols.append(v_col)

        # Also include dimension / categorical columns from this table (up to 8 columns total)
        for c in tbl_model.columns:
            if c.name not in cols and not c.name.lower().endswith("_id"):
                cols.append(c.name)
            if len(cols) >= 8:
                break

        col_clause = ", ".join(cols)
        query = f"SELECT {col_clause} FROM {primary_table}"

        # If time dimension present in table, order chronologically
        if time_col_in_tbl:
            query += f" ORDER BY {time_col_in_tbl} ASC"

        query += " LIMIT 1000"
        return query


analytical_data_extractor = AnalyticalDataExtractor()

