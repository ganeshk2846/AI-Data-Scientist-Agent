"""
SQLite persistence adapter for the agent-owned application store (agent_app.sqlite).
Maintains sessions, turn histories, active frames, preferences, and verified exemplars.
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.memory.models import (
    ActiveFrame,
    ReusableExemplar,
    SessionModel,
    TurnModel,
    UserPreference,
)


class MemoryStore:
    """Relational SQLite repository for conversational memory and agent application state."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or settings.APP_DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        conn.execute("PRAGMA journal_mode = WAL;")
        return conn

    def _init_db(self) -> None:
        """Initializes tables and indexes idempotently."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.executescript("""
                CREATE TABLE IF NOT EXISTS memory_sessions (
                    session_id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    active_frame_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS memory_turns (
                    turn_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    standalone_rewrite TEXT,
                    sql_executed TEXT,
                    artifact_ref_id TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (session_id) REFERENCES memory_sessions(session_id) ON DELETE CASCADE
                );

                CREATE INDEX IF NOT EXISTS idx_turns_session_created 
                ON memory_turns(session_id, created_at);

                CREATE TABLE IF NOT EXISTS memory_preferences (
                    user_id TEXT NOT NULL,
                    pref_key TEXT NOT NULL,
                    pref_value TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (user_id, pref_key)
                );

                CREATE TABLE IF NOT EXISTS memory_exemplars (
                    exemplar_id TEXT PRIMARY KEY,
                    domain TEXT NOT NULL,
                    natural_question TEXT NOT NULL,
                    verified_sql TEXT NOT NULL,
                    description TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
            """)
            conn.commit()
            logger.info("Initialized MemoryStore tables in %s", self.db_path)
        finally:
            conn.close()

    def get_or_create_session(self, session_id: str, user_id: str = "default_user", title: Optional[str] = None) -> SessionModel:
        conn = self._get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute("SELECT * FROM memory_sessions WHERE session_id = ?", (session_id,))
            row = cur.fetchone()
            if row:
                frame_data = json.loads(row["active_frame_json"])
                cur.execute("SELECT count(*) as cnt FROM memory_turns WHERE session_id = ?", (session_id,))
                cnt = cur.fetchone()["cnt"]
                return SessionModel(
                    session_id=row["session_id"],
                    user_id=row["user_id"],
                    title=row["title"],
                    created_at=row["created_at"],
                    updated_at=row["updated_at"],
                    active_frame=ActiveFrame(**frame_data),
                    turn_count=cnt,
                )

            # Create new session
            default_title = title or "New Business Inquiry"
            empty_frame = ActiveFrame()
            cur.execute(
                """
                INSERT INTO memory_sessions (session_id, user_id, title, created_at, updated_at, active_frame_json)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (session_id, user_id, default_title, now_iso, now_iso, json.dumps(empty_frame.model_dump())),
            )
            conn.commit()
            return SessionModel(
                session_id=session_id,
                user_id=user_id,
                title=default_title,
                created_at=now_iso,
                updated_at=now_iso,
                active_frame=empty_frame,
                turn_count=0,
            )
        finally:
            conn.close()

    def list_sessions(self, user_id: str = "default_user") -> List[SessionModel]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT s.*, count(t.turn_id) as turn_count 
                FROM memory_sessions s
                LEFT JOIN memory_turns t ON s.session_id = t.session_id
                WHERE s.user_id = ?
                GROUP BY s.session_id
                ORDER BY s.updated_at DESC
                """,
                (user_id,),
            )
            rows = cur.fetchall()
            sessions = []
            for r in rows:
                frame_data = json.loads(r["active_frame_json"])
                sessions.append(
                    SessionModel(
                        session_id=r["session_id"],
                        user_id=r["user_id"],
                        title=r["title"],
                        created_at=r["created_at"],
                        updated_at=r["updated_at"],
                        active_frame=ActiveFrame(**frame_data),
                        turn_count=r["turn_count"],
                    )
                )
            return sessions
        finally:
            conn.close()

    def save_turn(self, turn: TurnModel) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute(
                """
                INSERT INTO memory_turns 
                (turn_id, session_id, role, content, standalone_rewrite, sql_executed, artifact_ref_id, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    turn.turn_id,
                    turn.session_id,
                    turn.role,
                    turn.content,
                    turn.standalone_rewrite,
                    turn.sql_executed,
                    turn.artifact_ref_id,
                    turn.created_at,
                ),
            )
            cur.execute(
                "UPDATE memory_sessions SET updated_at = ? WHERE session_id = ?",
                (now_iso, turn.session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def get_recent_turns(self, session_id: str, limit: int = 3) -> List[TurnModel]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                SELECT * FROM memory_turns 
                WHERE session_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
                """,
                (session_id, limit),
            )
            rows = cur.fetchall()
            turns = [
                TurnModel(
                    turn_id=r["turn_id"],
                    session_id=r["session_id"],
                    role=r["role"],
                    content=r["content"],
                    standalone_rewrite=r["standalone_rewrite"],
                    sql_executed=r["sql_executed"],
                    artifact_ref_id=r["artifact_ref_id"],
                    created_at=r["created_at"],
                )
                for r in reversed(rows)
            ]
            return turns
        finally:
            conn.close()

    def update_active_frame(self, session_id: str, frame: ActiveFrame) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute(
                """
                UPDATE memory_sessions 
                SET active_frame_json = ?, updated_at = ?
                WHERE session_id = ?
                """,
                (json.dumps(frame.model_dump()), now_iso, session_id),
            )
            conn.commit()
        finally:
            conn.close()

    def clear_session(self, session_id: str) -> bool:
        """Clears all turns and resets active frame for a session without deleting the session container."""
        conn = self._get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute("DELETE FROM memory_turns WHERE session_id = ?", (session_id,))
            empty_frame = json.dumps(ActiveFrame().model_dump())
            cur.execute(
                "UPDATE memory_sessions SET active_frame_json = ?, updated_at = ? WHERE session_id = ?",
                (empty_frame, now_iso, session_id),
            )
            conn.commit()
            return True
        finally:
            conn.close()

    def delete_session(self, session_id: str) -> bool:
        """Deletes session and all associated turns."""
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("DELETE FROM memory_sessions WHERE session_id = ?", (session_id,))
            conn.commit()
            return cur.rowcount > 0
        finally:
            conn.close()

    def set_user_preference(self, user_id: str, key: str, value: str) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        now_iso = datetime.now(timezone.utc).isoformat()
        try:
            cur.execute(
                """
                INSERT INTO memory_preferences (user_id, pref_key, pref_value, updated_at)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(user_id, pref_key) DO UPDATE SET pref_value = excluded.pref_value, updated_at = excluded.updated_at
                """,
                (user_id, key, value, now_iso),
            )
            conn.commit()
        finally:
            conn.close()

    def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute("SELECT pref_key, pref_value FROM memory_preferences WHERE user_id = ?", (user_id,))
            rows = cur.fetchall()
            return {r["pref_key"]: r["pref_value"] for r in rows}
        finally:
            conn.close()

    def add_exemplar(self, exemplar: ReusableExemplar) -> None:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            cur.execute(
                """
                INSERT OR REPLACE INTO memory_exemplars 
                (exemplar_id, domain, natural_question, verified_sql, description, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    exemplar.exemplar_id,
                    exemplar.domain,
                    exemplar.natural_question,
                    exemplar.verified_sql,
                    exemplar.description,
                    exemplar.created_at,
                ),
            )
            conn.commit()
        finally:
            conn.close()

    def list_exemplars(self, domain: Optional[str] = None) -> List[ReusableExemplar]:
        conn = self._get_connection()
        cur = conn.cursor()
        try:
            if domain:
                cur.execute("SELECT * FROM memory_exemplars WHERE domain = ? ORDER BY created_at DESC", (domain,))
            else:
                cur.execute("SELECT * FROM memory_exemplars ORDER BY created_at DESC")
            rows = cur.fetchall()
            return [
                ReusableExemplar(
                    exemplar_id=r["exemplar_id"],
                    domain=r["domain"],
                    natural_question=r["natural_question"],
                    verified_sql=r["verified_sql"],
                    description=r["description"],
                    created_at=r["created_at"],
                )
                for r in rows
            ]
        finally:
            conn.close()


memory_store = MemoryStore()

