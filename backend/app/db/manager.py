"""
backend/app/db/manager.py
Single active database connection manager for the Conversational Data Scientist Agent.
Enforces the invariant: ONE USER -> ONE ACTIVE DATABASE CONNECTION -> ONE ENGINE AT A TIME.
Supports SQLite, PostgreSQL, and MySQL with safe connection pooling and state persistence.
"""

from pathlib import Path
import sqlite3
import threading
from typing import Any, Dict, Optional
from backend.app.core.config import settings
from backend.app.core.contracts import (
    ActiveDatabaseConfig,
    ConnectionStatus,
    DatabaseStatusResponse,
    SupportedEngine,
)
from backend.app.core.errors import DatabaseError
from backend.app.core.logging import logger
from backend.app.db.adapters.mysql import MySQLAdapter
from backend.app.db.adapters.postgres import PostgresAdapter
from backend.app.db.adapters.sqlite import SQLiteAdapter
from backend.app.db.base import BaseDatabaseAdapter
from backend.app.db.migration import run_agent_store_migration
from backend.app.db.security import (
    decrypt_connection_params,
    encrypt_connection_params,
)


class DatabaseConnectionManager:
    """Singleton manager controlling the single active database connection."""

    def __init__(self):
        self._lock = threading.RLock()
        self._active_adapter: Optional[BaseDatabaseAdapter] = None
        self._active_config: Optional[ActiveDatabaseConfig] = None
        self._initialized = False

    def initialize(self) -> None:
        """Initializes agent store and loads active database connection."""
        with self._lock:
            if self._initialized:
                return

            run_agent_store_migration()
            self._load_persisted_active_database()
            self._initialized = True

    def _load_persisted_active_database(self) -> None:
        """Loads active database from agent_app.sqlite or seeds baseline ecommerce.db."""
        conn = sqlite3.connect(str(settings.resolved_app_db_path))
        conn.row_factory = sqlite3.Row
        try:
            cur = conn.cursor()
            cur.execute("SELECT * FROM active_database_config WHERE id = 'active_db';")
            row = cur.fetchone()

            if row and row["status"] != ConnectionStatus.DISCONNECTED.value:
                # Reconnect persisted active database
                params = decrypt_connection_params(row["connection_params_enc"])
                engine_type = SupportedEngine(row["engine"])

                # A stored SQLite path comes from whichever machine last connected.
                # If that file is not on this machine, fall back to the configured
                # local database instead of starting with no active connection.
                stored_path = params.get("file_path")
                if engine_type == SupportedEngine.SQLITE and stored_path:
                    if not Path(stored_path).expanduser().exists():
                        baseline = settings.resolved_ecommerce_db_path
                        if baseline.exists():
                            logger.warning(
                                f"Stored database path '{stored_path}' is not present on this machine. "
                                f"Falling back to the configured database at '{baseline}'."
                            )
                            params = dict(params)
                            params["file_path"] = str(baseline)
                            row = dict(row)
                            row["name"] = baseline.name
                            row["fingerprint"] = None
                        else:
                            raise FileNotFoundError(
                                f"Stored database '{stored_path}' is missing and no local database "
                                f"was found at '{baseline}'. Connect a database through setup."
                            )

                config = ActiveDatabaseConfig(
                    id="active_db",
                    name=row["name"],
                    engine=engine_type,
                    file_path=params.get("file_path"),
                    host=params.get("host"),
                    port=params.get("port"),
                    database=params.get("database"),
                    username=params.get("username"),
                    status=ConnectionStatus(row["status"]),
                    fingerprint=row["fingerprint"],
                    read_only=True,
                )
                self._connect_adapter(config, params)
                self._active_config = config
                logger.info(f"Restored persisted active database: {config.name} ({config.engine})")
                return

            # If no active database is persisted, check if baseline ecommerce.db exists
            baseline_path = settings.resolved_ecommerce_db_path
            if baseline_path.exists():
                logger.info(f"Seeding baseline database: {baseline_path.name}")
                config = ActiveDatabaseConfig(
                    id="active_db",
                    name=baseline_path.name,
                    engine=SupportedEngine.SQLITE,
                    file_path=str(baseline_path),
                    status=ConnectionStatus.READY,
                    read_only=True,
                )
                params = {"file_path": str(baseline_path)}
                self._connect_adapter(config, params)
                self._persist_config(config, params)
                self._active_config = config
                try:
                    from backend.app.retrieval.semantics import dynamic_semantic_engine, is_ecommerce_compatible
                    fp = self._active_adapter.compute_fingerprint() if self._active_adapter else None
                    if fp:
                        from backend.app.schema.service import schema_service
                        cat = schema_service.profile_database(force_refresh=False)
                        if cat and is_ecommerce_compatible(cat):
                            dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=cat)
                except Exception as e:
                    logger.debug(f"Could not seed canonical metrics on init: {e}")
                logger.info(f"Successfully seeded baseline active database: {config.name}")

        except Exception as e:
            logger.warning(f"Could not initialize active database from store: {e}")
        finally:
            conn.close()

    def _connect_adapter(self, config: ActiveDatabaseConfig, params: Dict[str, Any]) -> None:
        """Instantiates and connects the appropriate engine adapter."""
        if config.engine == SupportedEngine.SQLITE:
            adapter = SQLiteAdapter(
                file_path=params.get("file_path") or config.file_path,
                name=config.name,
                read_only=config.read_only,
            )
        elif config.engine == SupportedEngine.POSTGRESQL:
            adapter = PostgresAdapter(
                host=params.get("host", "localhost"),
                port=params.get("port", 5432),
                database=params.get("database", "postgres"),
                username=params.get("username", "postgres"),
                password=params.get("password"),
                name=config.name,
                read_only=config.read_only,
            )
        elif config.engine == SupportedEngine.MYSQL:
            adapter = MySQLAdapter(
                host=params.get("host", "localhost"),
                port=params.get("port", 3306),
                database=params.get("database", "mysql"),
                username=params.get("username", "root"),
                password=params.get("password"),
                name=config.name,
                read_only=config.read_only,
            )
        else:
            raise DatabaseError(f"Unsupported database engine: {config.engine}")

        adapter.connect()
        self._active_adapter = adapter

    def _persist_config(self, config: ActiveDatabaseConfig, params: Dict[str, Any]) -> None:
        """Persists encrypted active database configuration in agent_app.sqlite."""
        conn = sqlite3.connect(str(settings.resolved_app_db_path))
        try:
            enc_params = encrypt_connection_params(params)
            fingerprint = self._active_adapter.compute_fingerprint() if self._active_adapter else None

            with conn:
                conn.execute(
                    """
                    INSERT INTO active_database_config (id, name, engine, connection_params_enc, status, fingerprint, updated_at)
                    VALUES ('active_db', ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(id) DO UPDATE SET
                        name = excluded.name,
                        engine = excluded.engine,
                        connection_params_enc = excluded.connection_params_enc,
                        status = excluded.status,
                        fingerprint = excluded.fingerprint,
                        updated_at = CURRENT_TIMESTAMP;
                    """,
                    (config.name, config.engine.value, enc_params, config.status.value, fingerprint),
                )
        finally:
            conn.close()

    def get_active_adapter(self) -> BaseDatabaseAdapter:
        """Returns the currently active database adapter or raises error."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            if not self._active_adapter or not self._active_adapter.is_connected:
                raise DatabaseError("No active database connected. Please connect a database first.")
            return self._active_adapter

    def get_active_config(self) -> Optional[ActiveDatabaseConfig]:
        """Returns current active database configuration."""
        with self._lock:
            if not self._initialized:
                self.initialize()
            return self._active_config

    def connect_database(
        self,
        config: ActiveDatabaseConfig,
        credentials: Optional[Dict[str, Any]] = None,
    ) -> BaseDatabaseAdapter:
        """
        Connects to a new database and makes it active, safely disposing any previous connection.
        """
        with self._lock:
            # 1. Gracefully close previous active connection
            if self._active_adapter:
                logger.info(f"Disposing previous database connection: {self._active_adapter.name}")
                self._active_adapter.disconnect()
                self._active_adapter = None

            # 2. Prepare params
            params = credentials or {}
            if config.file_path:
                params["file_path"] = config.file_path
            if config.host:
                params["host"] = config.host
            if config.port:
                params["port"] = config.port
            if config.database:
                params["database"] = config.database
            if config.username:
                params["username"] = config.username

            # 3. Instantiate and connect new adapter
            self._connect_adapter(config, params)

            # 4. Compute fingerprint and update state
            fp = self._active_adapter.compute_fingerprint()
            updated_config = ActiveDatabaseConfig(
                id="active_db",
                name=config.name,
                engine=config.engine,
                file_path=config.file_path,
                host=config.host,
                port=config.port,
                database=config.database,
                username=config.username,
                status=ConnectionStatus.READY,
                fingerprint=fp,
                read_only=config.read_only,
            )

            # 5. Persist to agent store
            prev_fp = self._active_config.fingerprint if self._active_config else None
            self._persist_config(updated_config, params)
            self._active_config = updated_config

            # 6. Invalidate previous schema, retrieval, and supervisor caches
            try:
                from backend.app.retrieval.hybrid import hybrid_retriever
                hybrid_retriever.catalog = None
                hybrid_retriever.corpus = None
                hybrid_retriever.bm25 = None
                hybrid_retriever.vector_store = None
                from backend.app.schema.service import schema_service
                schema_service.clear_cache()
                if prev_fp and prev_fp != fp:
                    from backend.app.orchestration.supervisor import agentic_supervisor
                    agentic_supervisor.clear_database_cache(prev_fp)
                    from backend.app.analysis.orchestrator import analytical_orchestrator
                    analytical_orchestrator.clear_database_cache(prev_fp)
            except Exception as e:
                logger.debug(f"Retrieval and supervisor cache reset on activation: {e}")

            # 7. Check e-commerce compatibility for canonical metric seeding
            try:
                from backend.app.retrieval.semantics import dynamic_semantic_engine, is_ecommerce_compatible
                from backend.app.schema.service import schema_service
                cat = schema_service.profile_database(force_refresh=True)
                if cat and is_ecommerce_compatible(cat):
                    dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=cat)
            except Exception as e:
                logger.debug(f"Post-activation canonical metric check: {e}")

            logger.info(f"Successfully activated database: {config.name} ({config.engine})")
            return self._active_adapter

    def disconnect_database(self) -> None:
        """Gracefully disconnects the active database."""
        with self._lock:
            if self._active_adapter:
                self._active_adapter.disconnect()
                self._active_adapter = None

            if self._active_config:
                self._active_config = ActiveDatabaseConfig(
                    id="active_db",
                    name=self._active_config.name,
                    engine=self._active_config.engine,
                    status=ConnectionStatus.DISCONNECTED,
                    read_only=True,
                )

            # Update status in store
            conn = sqlite3.connect(str(settings.resolved_app_db_path))
            try:
                with conn:
                    conn.execute(
                        "UPDATE active_database_config SET status = 'DISCONNECTED', updated_at = CURRENT_TIMESTAMP WHERE id = 'active_db';"
                    )
            finally:
                conn.close()

            # Invalidate in-memory schema and retrieval caches
            try:
                from backend.app.retrieval.hybrid import hybrid_retriever
                hybrid_retriever.catalog = None
                hybrid_retriever.corpus = None
                hybrid_retriever.bm25 = None
                hybrid_retriever.vector_store = None
            except Exception as e:
                logger.debug(f"Retrieval cache reset on disconnect: {e}")

            logger.info("Active database disconnected successfully.")

    def get_status(self) -> DatabaseStatusResponse:
        """Returns the current database readiness status."""
        with self._lock:
            if not self._initialized:
                self.initialize()

            if not self._active_adapter or not self._active_adapter.is_connected:
                return DatabaseStatusResponse(
                    connected=False,
                    status=ConnectionStatus.DISCONNECTED,
                    read_only=True,
                )

            try:
                tables = self._active_adapter.get_table_names()
                total_rows = sum(self._active_adapter.get_table_row_count(t) for t in tables)
                fp = self._active_adapter.compute_fingerprint()

                return DatabaseStatusResponse(
                    connected=True,
                    engine=self._active_adapter.engine_type,
                    database_name=self._active_adapter.name,
                    status=ConnectionStatus.READY,
                    tables_count=len(tables),
                    total_rows=total_rows,
                    fingerprint=fp,
                    read_only=self._active_adapter.read_only,
                )
            except Exception as e:
                logger.error(f"Error checking active database status: {e}")
                return DatabaseStatusResponse(
                    connected=False,
                    status=ConnectionStatus.ERROR,
                    error_message=str(e),
                )


# Global singleton instance
db_manager = DatabaseConnectionManager()
