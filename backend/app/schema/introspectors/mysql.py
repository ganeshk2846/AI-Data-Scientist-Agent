"""
backend/app/schema/introspectors/mysql.py
MySQL schema introspector using SQLAlchemy Inspector and metadata.
"""

from typing import List
from sqlalchemy import inspect
from backend.app.db.adapters.mysql import MySQLAdapter
from backend.app.schema.introspectors.base import BaseIntrospector
from backend.app.schema.models import ColumnModel, ForeignKeyModel, IndexModel


class MySQLIntrospector(BaseIntrospector):
    """Discovers MySQL schema metadata using SQLAlchemy inspector."""

    def __init__(self, adapter: MySQLAdapter):
        self.adapter = adapter

    def introspect_tables(self) -> List[str]:
        """Discovers tables in active MySQL database."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        return sorted(inspector.get_table_names())

    def introspect_views(self) -> List[str]:
        """Discovers views in active MySQL database."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        return sorted(inspector.get_view_names())

    def introspect_columns(self, table_name: str) -> List[ColumnModel]:
        """Discovers column definitions and data types."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        cols = inspector.get_columns(table_name)
        pk_cols = set(self.introspect_primary_keys(table_name))
        fks = self.introspect_foreign_keys(table_name)
        fks_map = {fk.source_column: (fk.target_table, fk.target_column) for fk in fks}

        result: List[ColumnModel] = []
        for c in cols:
            col_name = c["name"]
            type_str = str(c["type"])
            is_pk = col_name in pk_cols
            is_fk = col_name in fks_map
            fk_target_tbl, fk_target_col = fks_map.get(col_name, (None, None))

            col_lower = col_name.lower()
            type_upper = type_str.upper()
            is_date = any(k in col_lower for k in ['date', 'time', 'timestamp', 'at', '_year', '_month', 'day']) or 'DATE' in type_upper or 'TIME' in type_upper
            is_numeric = any(k in type_upper for k in ['INT', 'REAL', 'FLOA', 'DOUB', 'DEC', 'NUM']) or any(k in col_lower for k in ['amount', 'price', 'cost', 'total', 'revenue', 'count', 'score', 'rate'])

            result.append(
                ColumnModel(
                    name=col_name,
                    sqlite_type=type_str,
                    is_pk=is_pk,
                    not_null=not c.get("nullable", True),
                    default_value=str(c.get("default")) if c.get("default") is not None else None,
                    is_fk=is_fk,
                    fk_target_table=fk_target_tbl,
                    fk_target_column=fk_target_col,
                    is_date_candidate=is_date,
                    is_numeric_candidate=is_numeric,
                )
            )
        return result

    def introspect_primary_keys(self, table_name: str) -> List[str]:
        """Returns primary key column names."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        pk_constraint = inspector.get_pk_constraint(table_name)
        return pk_constraint.get("constrained_columns", [])

    def introspect_foreign_keys(self, table_name: str) -> List[ForeignKeyModel]:
        """Discovers foreign keys."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        raw_fks = inspector.get_foreign_keys(table_name)
        result: List[ForeignKeyModel] = []
        for fk in raw_fks:
            constrained_cols = fk.get("constrained_columns", [])
            referred_cols = fk.get("referred_columns", [])
            referred_table = fk.get("referred_table", "")
            for src, tgt in zip(constrained_cols, referred_cols):
                result.append(
                    ForeignKeyModel(
                        source_column=src,
                        target_table=referred_table,
                        target_column=tgt,
                    )
                )
        return result

    def introspect_indexes(self, table_name: str) -> List[IndexModel]:
        """Discovers indexes."""
        if not self.adapter.is_connected:
            self.adapter.connect()
        inspector = inspect(self.adapter._engine)
        raw_idxs = inspector.get_indexes(table_name)
        result: List[IndexModel] = []
        for idx in raw_idxs:
            result.append(
                IndexModel(
                    name=idx.get("name", ""),
                    unique=bool(idx.get("unique", False)),
                    columns=idx.get("column_names", []),
                )
            )
        return result

    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count for table."""
        return self.adapter.get_table_row_count(table_name)
