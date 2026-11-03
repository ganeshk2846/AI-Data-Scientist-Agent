"""
backend/app/db/migration.py
Non-destructive schema migration for agent_app.sqlite.
Establishes active_database_config and semantic_metrics tables while preserving historical memory.
"""

from pathlib import Path
import sqlite3
from typing import Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger


def run_agent_store_migration(app_db_path: Optional[Path] = None) -> None:
    """Executes transactional DDL on agent_app.sqlite to support Version 2 features."""
    target_path = app_db_path or settings.resolved_app_db_path
    target_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(str(target_path))
    try:
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")

        with conn:
            # 1. Create Active Database Configuration Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_database_config (
                    id TEXT PRIMARY KEY DEFAULT 'active_db',
                    name TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    connection_params_enc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    fingerprint TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 2. Create Active LLM Configuration Table (Groq only)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS active_llm_config (
                    id TEXT PRIMARY KEY DEFAULT 'active_llm',
                    provider TEXT NOT NULL DEFAULT 'groq',
                    model TEXT NOT NULL,
                    api_key_enc TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 3. Create Saved Databases Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS saved_databases (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    engine TEXT NOT NULL,
                    connection_params_enc TEXT NOT NULL,
                    fingerprint TEXT,
                    is_active INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # 4. Check semantic_metrics table
            cur = conn.cursor()
            cur.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='semantic_metrics';")
            table_row = cur.fetchone()

            if not table_row:
                conn.execute("""
                    CREATE TABLE semantic_metrics (
                        id TEXT PRIMARY KEY,
                        metric_key TEXT NOT NULL,
                        display_name TEXT NOT NULL,
                        formula_sql TEXT NOT NULL,
                        status TEXT NOT NULL,
                        derivation_type TEXT NOT NULL,
                        verified_by TEXT,
                        description TEXT,
                        confidence_score REAL DEFAULT 0.5,
                        fingerprint TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(fingerprint, metric_key)
                    );
                """)
                conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_metrics_fp ON semantic_metrics(fingerprint);")
            else:
                sql_def = table_row[0]
                # If table exists with legacy UNIQUE(metric_key) constraint instead of UNIQUE(fingerprint, metric_key)
                if "UNIQUE(fingerprint, metric_key)" not in sql_def and "UNIQUE (fingerprint, metric_key)" not in sql_def:
                    # Non-destructive migration to composite uniqueness
                    conn.execute("""
                        CREATE TABLE IF NOT EXISTS semantic_metrics_v2 (
                            id TEXT PRIMARY KEY,
                            metric_key TEXT NOT NULL,
                            display_name TEXT NOT NULL,
                            formula_sql TEXT NOT NULL,
                            status TEXT NOT NULL,
                            derivation_type TEXT NOT NULL,
                            verified_by TEXT,
                            description TEXT,
                            confidence_score REAL DEFAULT 0.5,
                            fingerprint TEXT NOT NULL,
                            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                            UNIQUE(fingerprint, metric_key)
                        );
                    """)
                    conn.execute("""
                        INSERT OR REPLACE INTO semantic_metrics_v2
                        SELECT id, metric_key, display_name, formula_sql, status, derivation_type, verified_by, description, confidence_score,
                               CASE WHEN fingerprint IS NULL OR fingerprint = 'default' THEN '9c51abb2f2569a4a1e4ef4a0d1b806294b3f972ca0527d12f34ae9285e9e15ab' ELSE fingerprint END,
                               created_at, updated_at
                        FROM semantic_metrics;
                    """)
                    conn.execute("DROP TABLE semantic_metrics;")
                    conn.execute("ALTER TABLE semantic_metrics_v2 RENAME TO semantic_metrics;")
                    conn.execute("CREATE INDEX IF NOT EXISTS idx_semantic_metrics_fp ON semantic_metrics(fingerprint);")

        logger.info(f"Verified agent_app.sqlite schema migration at {target_path}")

    except Exception as e:
        logger.error(f"Migration failed on {target_path}: {e}")
        raise e
    finally:
        conn.close()
