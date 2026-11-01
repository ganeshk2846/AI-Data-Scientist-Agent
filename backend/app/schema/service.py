"""
Schema introspection and profiling service.
Inspects ecommerce.sqlite in read-only mode, extracts schema and quality metrics,
and caches results idempotently in the agent-owned store.
"""

import hashlib
import json
import os
from pathlib import Path
import sqlite3
from typing import Callable, Dict, List, Optional
from backend.app.core.config import settings, REPO_ROOT
from backend.app.core.errors import DatabaseError
from backend.app.core.logging import logger
from backend.app.db.connection import get_readonly_connection
from backend.app.schema.models import (
    ColumnModel,
    DatabaseCatalog,
    ForeignKeyModel,
    IndexModel,
    TableModel,
)

CACHE_DIR = REPO_ROOT / "data"
CATALOG_CACHE_FILE = CACHE_DIR / "schema_catalog_cache.json"


class SchemaService:
    """Introspects and profiles the database schema in read-only mode."""

    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.resolved_ecommerce_db_path
        self._cached_catalog: Optional[DatabaseCatalog] = None

    def compute_source_fingerprint(self) -> str:
        """
        Computes a deterministic fingerprint of the source database based on:
        - File size
        - Modification timestamp
        - SHA256 of sqlite_master schema definitions
        """
        if not self.db_path.exists():
            raise DatabaseError(f"Database file not found: {self.db_path}")

        stat = self.db_path.stat()
        hasher = hashlib.sha256()
        hasher.update(f"{stat.st_size}_{stat.st_mtime}".encode("utf-8"))

        with get_readonly_connection() as conn:
            cur = conn.cursor()
            cur.execute("SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name;")
            rows = cur.fetchall()
            for r in rows:
                hasher.update(f"{r[0]}:{r[1]}:{r[3] or ''}".encode("utf-8"))

        return hasher.hexdigest()

    def get_cached_catalog(self) -> Optional[DatabaseCatalog]:
        """Loads cached catalog if it exists and matches the current database fingerprint."""
        if self._cached_catalog is not None:
            return self._cached_catalog

        if not CATALOG_CACHE_FILE.exists():
            return None

        try:
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            catalog = DatabaseCatalog.model_validate(data)

            # Check if fingerprint still matches
            current_fp = self.compute_source_fingerprint()
            if catalog.source_fingerprint == current_fp:
                self._cached_catalog = catalog
                logger.info(f"Loaded schema catalogue from cache (fingerprint: {current_fp[:8]}...)")
                return catalog
            else:
                logger.info("Cached catalogue fingerprint is stale. Will re-profile.")
                return None
        except Exception as e:
            logger.warning(f"Failed to read catalogue cache: {e}")
            return None

    def save_catalog_to_cache(self, catalog: DatabaseCatalog) -> None:
        """Persists catalog to local application store."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(catalog.model_dump(mode="json"), f, indent=2)
        self._cached_catalog = catalog
        logger.info(f"Persisted schema catalogue cache to: {CATALOG_CACHE_FILE}")

    def profile_database(
        self,
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> DatabaseCatalog:
        """
        Performs full introspection and data profiling across all tables.
        Returns DatabaseCatalog instance.
        """
        fingerprint = self.compute_source_fingerprint()

        if not force_refresh:
            cached = self.get_cached_catalog()
            if cached and cached.source_fingerprint == fingerprint:
                if progress_callback:
                    progress_callback(cached.total_tables, cached.total_tables, "Loaded from cache")
                return cached

        logger.info(f"Starting schema introspection on {self.db_path} (mode=ro)...")

        with get_readonly_connection() as conn:
            cur = conn.cursor()

            # Discovered tables
            cur.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;"
            )
            tables = [r[0] for r in cur.fetchall()]

            total_tables = len(tables)
            total_rows = 0
            catalog_tables: Dict[str, TableModel] = {}
            fk_graph: List[Dict[str, str]] = []

            for idx, tbl in enumerate(tables, start=1):
                if progress_callback:
                    progress_callback(idx, total_tables, tbl)

                # Row count
                cur.execute(f'SELECT COUNT(*) FROM "{tbl}";')
                row_cnt = cur.fetchone()[0]
                total_rows += row_cnt

                # Columns (cid, name, type, notnull, dflt_value, pk)
                cur.execute(f'PRAGMA table_info("{tbl}");')
                raw_cols = cur.fetchall()

                # Foreign keys (id, seq, table, from, to, on_update, on_delete, match)
                cur.execute(f'PRAGMA foreign_key_list("{tbl}");')
                raw_fks = cur.fetchall()
                fks_by_col = {}
                table_fks = []
                for fk in raw_fks:
                    fk_model = ForeignKeyModel(
                        source_column=fk[3],
                        target_table=fk[2],
                        target_column=fk[4],
                        on_update=fk[5],
                        on_delete=fk[6],
                    )
                    table_fks.append(fk_model)
                    fks_by_col[fk[3]] = (fk[2], fk[4])
                    fk_graph.append({
                        "source_table": tbl,
                        "source_column": fk[3],
                        "target_table": fk[2],
                        "target_column": fk[4],
                    })

                # Indexes
                cur.execute(f'PRAGMA index_list("{tbl}");')
                raw_idxs = cur.fetchall()
                table_idxs = []
                for idx_item in raw_idxs:
                    idx_name = idx_item[1]
                    cur.execute(f'PRAGMA index_info("{idx_name}");')
                    idx_cols = [c[2] for c in cur.fetchall()]
                    table_idxs.append(
                        IndexModel(name=idx_name, unique=bool(idx_item[2]), columns=idx_cols)
                    )

                # Profile columns
                table_cols = []
                pk_cols = []
                for c in raw_cols:
                    cid, col_name, col_type, notnull, dflt, pk = c
                    is_pk = bool(pk)
                    if is_pk:
                        pk_cols.append(col_name)

                    is_fk = col_name in fks_by_col
                    fk_target_tbl, fk_target_col = fks_by_col.get(col_name, (None, None))

                    # Statistical profiling query
                    null_cnt = 0
                    dist_cnt = 0
                    min_v = None
                    max_v = None
                    sample_vals: List[str] = []

                    try:
                        cur.execute(f'''
                            SELECT 
                                SUM(CASE WHEN "{col_name}" IS NULL THEN 1 ELSE 0 END),
                                COUNT(DISTINCT "{col_name}"),
                                MIN("{col_name}"),
                                MAX("{col_name}")
                            FROM "{tbl}";
                        ''')
                        stats = cur.fetchone()
                        null_cnt = stats[0] if stats[0] is not None else 0
                        dist_cnt = stats[1] if stats[1] is not None else 0
                        min_v = stats[2]
                        max_v = stats[3]

                        # Safe sample values for low-cardinality categorical fields (excluding IDs and PKs)
                        if not is_pk and not is_fk and dist_cnt > 0 and dist_cnt <= 10:
                            cur.execute(f'''
                                SELECT DISTINCT "{col_name}" 
                                FROM "{tbl}" 
                                WHERE "{col_name}" IS NOT NULL 
                                LIMIT 10;
                            ''')
                            sample_vals = [str(r[0]) for r in cur.fetchall()]
                    except Exception as err:
                        logger.debug(f"Profiling error on {tbl}.{col_name}: {err}")

                    # Heuristic detection for candidates
                    col_lower = col_name.lower()
                    type_upper = (col_type or "").upper()
                    is_date = any(k in col_lower for k in ['date', 'time', 'timestamp', 'at', '_year', '_month', 'day']) or 'DATE' in type_upper or 'TIME' in type_upper
                    is_numeric = any(k in type_upper for k in ['INT', 'REAL', 'FLOA', 'DOUB', 'DEC', 'NUM']) or any(k in col_lower for k in ['amount', 'price', 'cost', 'total', 'revenue', 'count', 'score', 'rate'])

                    null_pct = round((null_cnt / row_cnt * 100), 2) if row_cnt > 0 else 0.0

                    table_cols.append(
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
                            null_count=null_cnt,
                            null_percentage=null_pct,
                            distinct_count=dist_cnt,
                            min_sample=str(min_v)[:60] if min_v is not None else None,
                            max_sample=str(max_v)[:60] if max_v is not None else None,
                            sample_values=sample_vals,
                        )
                    )

                catalog_tables[tbl] = TableModel(
                    name=tbl,
                    row_count=row_cnt,
                    columns=table_cols,
                    foreign_keys=table_fks,
                    indexes=table_idxs,
                    primary_key_columns=pk_cols,
                )

        catalog = DatabaseCatalog(
            source_fingerprint=fingerprint,
            database_path=str(self.db_path),
            total_tables=total_tables,
            total_rows=total_rows,
            tables=catalog_tables,
            foreign_key_graph=fk_graph,
        )

        self.save_catalog_to_cache(catalog)
        return catalog


schema_service = SchemaService()
