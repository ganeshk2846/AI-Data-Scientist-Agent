"""
backend/app/schema/service.py
Dynamic, multi-engine schema introspection and adaptive profiling service.
Automatically adapts to whichever database is currently active in DatabaseConnectionManager.
Caches active schema catalog in data/active_catalog.json with fingerprint-based cache invalidation.
"""

import json
from pathlib import Path
from typing import Callable, Dict, List, Optional, Union
from backend.app.core.config import REPO_ROOT, settings
from backend.app.core.contracts import SupportedEngine
from backend.app.core.errors import DatabaseError
from backend.app.core.logging import logger
from backend.app.db.adapters.mysql import MySQLAdapter
from backend.app.db.adapters.postgres import PostgresAdapter
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.manager import db_manager
from backend.app.schema.introspectors.base import BaseIntrospector
from backend.app.schema.introspectors.mysql import MySQLIntrospector
from backend.app.schema.introspectors.postgres import PostgresIntrospector
from backend.app.schema.introspectors.sqlite import SQLiteIntrospector
from backend.app.schema.models import (
    ColumnModel,
    DatabaseCatalog,
    ForeignKeyModel,
    IndexModel,
    TableModel,
)
from backend.app.schema.profiler import AdaptiveSamplingProfiler

CACHE_DIR = REPO_ROOT / "data"
ACTIVE_CATALOG_FILE = CACHE_DIR / "active_catalog.json"
LEGACY_CATALOG_FILE = CACHE_DIR / "schema_catalog_cache.json"


class SchemaService:
    """Introspects and profiles whichever database is currently active."""

    def __init__(self, db_path: Optional[Union[str, Path]] = None):
        self._cached_catalog: Optional[DatabaseCatalog] = None
        self._custom_db_path = Path(db_path) if db_path else None
        self._custom_adapter = None
        if self._custom_db_path:
            self._custom_adapter = SQLiteAdapter(file_path=self._custom_db_path, read_only=True)
            self._custom_adapter.connect()

    def _get_introspector(self) -> BaseIntrospector:
        """Instantiates the introspector matching the active database engine."""
        if self._custom_adapter:
            return SQLiteIntrospector(self._custom_adapter)
        adapter = db_manager.get_active_adapter()
        if adapter.engine_type == SupportedEngine.SQLITE:
            return SQLiteIntrospector(adapter)
        elif adapter.engine_type == SupportedEngine.POSTGRESQL:
            return PostgresIntrospector(adapter)
        elif adapter.engine_type == SupportedEngine.MYSQL:
            return MySQLIntrospector(adapter)
        else:
            raise DatabaseError(f"Unsupported database engine: {adapter.engine_type}")

    def compute_source_fingerprint(self) -> str:
        """Computes deterministic fingerprint of the active database."""
        if self._custom_adapter:
            return self._custom_adapter.compute_fingerprint()
        adapter = db_manager.get_active_adapter()
        return adapter.compute_fingerprint()

    def get_cached_catalog(self) -> Optional[DatabaseCatalog]:
        """Loads cached active catalog if fingerprint matches."""
        if self._cached_catalog is not None:
            return self._cached_catalog

        # Check active_catalog.json or legacy cache
        cache_file = ACTIVE_CATALOG_FILE if ACTIVE_CATALOG_FILE.exists() else LEGACY_CATALOG_FILE
        if not cache_file.exists():
            return None

        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            catalog = DatabaseCatalog.model_validate(data)

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
        """Persists catalog to active_catalog.json and legacy cache."""
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        dump = catalog.model_dump(mode="json")
        for target in [ACTIVE_CATALOG_FILE, LEGACY_CATALOG_FILE]:
            with open(target, "w", encoding="utf-8") as f:
                json.dump(dump, f, indent=2)
        self._cached_catalog = catalog
        logger.info(f"Persisted schema catalogue to: {ACTIVE_CATALOG_FILE}")

    def clear_cache(self) -> None:
        """Evicts in-memory and disk catalog caches on database disconnect."""
        self._cached_catalog = None
        for target in [ACTIVE_CATALOG_FILE, LEGACY_CATALOG_FILE]:
            if target.exists():
                try:
                    target.unlink()
                except Exception:
                    pass
        logger.info("Evicted schema catalog caches.")

    def profile_database(
        self,
        force_refresh: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None,
    ) -> DatabaseCatalog:
        """
        Performs dynamic introspection and adaptive profiling across all tables
        of the currently connected database.
        """
        if self._custom_adapter:
            adapter = self._custom_adapter
        else:
            adapter = db_manager.get_active_adapter()
        fingerprint = adapter.compute_fingerprint()

        if not force_refresh and not self._custom_adapter:
            cached = self.get_cached_catalog()
            if cached and cached.source_fingerprint == fingerprint:
                if progress_callback:
                    progress_callback(cached.total_tables, cached.total_tables, "Loaded from cache")
                return cached

        logger.info(f"Starting dynamic schema introspection on {adapter.name} ({adapter.engine_type})...")
        introspector = self._get_introspector()
        profiler = AdaptiveSamplingProfiler(adapter)

        tables = introspector.introspect_tables()
        total_tables = len(tables)
        total_rows = 0
        catalog_tables: Dict[str, TableModel] = {}
        fk_graph: List[Dict[str, str]] = []

        for idx, tbl in enumerate(tables, start=1):
            if progress_callback:
                progress_callback(idx, total_tables, tbl)

            # 1. Discover basic metadata
            row_cnt = introspector.get_table_row_count(tbl)
            total_rows += row_cnt
            raw_columns = introspector.introspect_columns(tbl)
            pks = introspector.introspect_primary_keys(tbl)
            fks = introspector.introspect_foreign_keys(tbl)
            idxs = introspector.introspect_indexes(tbl)

            for fk in fks:
                fk_graph.append({
                    "source_table": tbl,
                    "source_column": fk.source_column,
                    "target_table": fk.target_table,
                    "target_column": fk.target_column,
                })

            # 2. Adaptive statistical profiling
            profiled_columns = profiler.profile_table_columns(tbl, row_cnt, raw_columns)

            catalog_tables[tbl] = TableModel(
                name=tbl,
                row_count=row_cnt,
                columns=profiled_columns,
                foreign_keys=fks,
                indexes=idxs,
                primary_key_columns=pks,
            )

        catalog = DatabaseCatalog(
            source_fingerprint=fingerprint,
            database_path=adapter.name,
            total_tables=total_tables,
            total_rows=total_rows,
            tables=catalog_tables,
            foreign_key_graph=fk_graph,
        )

        if not self._custom_adapter:
            self.save_catalog_to_cache(catalog)
        return catalog


schema_service = SchemaService()
