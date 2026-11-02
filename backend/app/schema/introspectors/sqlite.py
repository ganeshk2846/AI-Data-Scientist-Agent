"""
backend/app/schema/introspectors/sqlite.py
SQLite-specific schema introspector using PRAGMAs and sqlite_master.
"""

from typing import List, Tuple
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.schema.introspectors.base import BaseIntrospector
from backend.app.schema.models import ColumnModel, ForeignKeyModel, IndexModel


class SQLiteIntrospector(BaseIntrospector):
    """Discovers SQLite schema metadata using native PRAGMA commands."""

    def __init__(self, adapter: SQLiteAdapter):
        self.adapter = adapter

    def introspect_tables(self) -> List[str]:
        """Discovers user tables from sqlite_master."""
        res = self.adapter.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
        )
        return [row["name"] for row in res.rows]

    def introspect_views(self) -> List[str]:
        """Discovers user views from sqlite_master."""
        res = self.adapter.execute_query(
            "SELECT name FROM sqlite_master WHERE type='view' ORDER BY name;"
        )
        return [row["name"] for row in res.rows]

    def introspect_columns(self, table_name: str) -> List[ColumnModel]:
        """Extracts column definitions via PRAGMA table_info."""
        columns: List[ColumnModel] = []
        with self.adapter.raw_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'PRAGMA table_info("{table_name}");')
            raw_cols = cur.fetchall()

            # Also get foreign keys to map is_fk flags
            cur.execute(f'PRAGMA foreign_key_list("{table_name}");')
            raw_fks = cur.fetchall()
            fks_map = {fk[3]: (fk[2], fk[4]) for fk in raw_fks}

            for c in raw_cols:
                cid, col_name, col_type, notnull, dflt, pk = c
                is_pk = bool(pk)
                is_fk = col_name in fks_map
                fk_target_tbl, fk_target_col = fks_map.get(col_name, (None, None))

                col_lower = col_name.lower()
                type_upper = (col_type or "").upper()
                is_date = any(k in col_lower for k in ['date', 'time', 'timestamp', 'at', '_year', '_month', 'day']) or 'DATE' in type_upper or 'TIME' in type_upper
                is_numeric = any(k in type_upper for k in ['INT', 'REAL', 'FLOA', 'DOUB', 'DEC', 'NUM']) or any(k in col_lower for k in ['amount', 'price', 'cost', 'total', 'revenue', 'count', 'score', 'rate'])

                columns.append(
                    ColumnModel(
                        name=col_name,
                        sqlite_type=col_type or "TEXT",
                        is_pk=is_pk,
                        not_null=bool(notnull),
                        default_value=str(dflt) if dflt is not None else None,
                        is_fk=is_fk,
                        fk_target_table=fk_target_tbl,
                        fk_target_column=fk_target_col,
                        is_date_candidate=is_date,
                        is_numeric_candidate=is_numeric,
                    )
                )
        return columns

    def introspect_primary_keys(self, table_name: str) -> List[str]:
        """Returns primary key column names."""
        with self.adapter.raw_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'PRAGMA table_info("{table_name}");')
            return [c[1] for c in cur.fetchall() if c[5] > 0]

    def introspect_foreign_keys(self, table_name: str) -> List[ForeignKeyModel]:
        """Discovers foreign keys via PRAGMA foreign_key_list."""
        fks: List[ForeignKeyModel] = []
        with self.adapter.raw_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'PRAGMA foreign_key_list("{table_name}");')
            for fk in cur.fetchall():
                fks.append(
                    ForeignKeyModel(
                        source_column=fk[3],
                        target_table=fk[2],
                        target_column=fk[4],
                        on_update=fk[5],
                        on_delete=fk[6],
                    )
                )
        return fks

    def introspect_indexes(self, table_name: str) -> List[IndexModel]:
        """Discovers indexes via PRAGMA index_list."""
        idxs: List[IndexModel] = []
        with self.adapter.raw_connection() as conn:
            cur = conn.cursor()
            cur.execute(f'PRAGMA index_list("{table_name}");')
            raw_idxs = cur.fetchall()
            for item in raw_idxs:
                idx_name = item[1]
                cur.execute(f'PRAGMA index_info("{idx_name}");')
                cols = [c[2] for c in cur.fetchall()]
                idxs.append(
                    IndexModel(name=idx_name, unique=bool(item[2]), columns=cols)
                )
        return idxs

    def get_table_row_count(self, table_name: str) -> int:
        """Returns row count for specified table."""
        return self.adapter.get_table_row_count(table_name)
