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

            # 2. Create Active Semantic Metrics Table
            conn.execute("""
                CREATE TABLE IF NOT EXISTS semantic_metrics (
                    id TEXT PRIMARY KEY,
                    metric_key TEXT NOT NULL UNIQUE,
                    display_name TEXT NOT NULL,
                    formula_sql TEXT NOT NULL,
                    status TEXT NOT NULL,
                    derivation_type TEXT NOT NULL,
                    verified_by TEXT,
                    description TEXT,
                    confidence_score REAL DEFAULT 0.5,
                    fingerprint TEXT DEFAULT 'default',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)

            # Non-destructive check for fingerprint column
            cur = conn.cursor()
            cur.execute("PRAGMA table_info(semantic_metrics);")
            cols = [r[1] for r in cur.fetchall()]
            if "fingerprint" not in cols:
                conn.execute("ALTER TABLE semantic_metrics ADD COLUMN fingerprint TEXT DEFAULT 'default';")

        logger.info(f"Verified agent_app.sqlite schema migration at {target_path}")

    except Exception as e:
        logger.error(f"Migration failed on {target_path}: {e}")
        raise e
    finally:
        conn.close()
