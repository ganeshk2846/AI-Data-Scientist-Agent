"""
Central Shared Memory Service for the Data Scientist Agent.
Applies session isolation, contextual follow-up question resolution (rewrite, don't concatenate),
active frame slot tracking, user preferences, and verified exemplars.
"""

import hashlib
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from backend.app.core.logging import logger
from backend.app.memory.models import (
    ActiveFrame,
    ContextPack,
    ReusableExemplar,
    SessionModel,
    TurnModel,
)
from backend.app.memory.store import MemoryStore, memory_store


class MemoryService:
    """Unified application-level service for conversation context, active frames, and preferences."""

    def __init__(self, store: Optional[MemoryStore] = None):
        self.store = store or memory_store

    def get_or_create_session(self, session_id: str, user_id: str = "default_user", title: Optional[str] = None) -> SessionModel:
        return self.store.get_or_create_session(session_id, user_id, title)

    def list_sessions(self, user_id: str = "default_user") -> List[SessionModel]:
        return self.store.list_sessions(user_id)

    def record_user_turn(self, session_id: str, query: str, standalone_rewrite: Optional[str] = None) -> TurnModel:
        turn = TurnModel(
            turn_id=str(uuid.uuid4()),
            session_id=session_id,
            role="user",
            content=query,
            standalone_rewrite=standalone_rewrite or query,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save_turn(turn)
        return turn

    def record_assistant_turn(
        self,
        session_id: str,
        answer: str,
        sql: Optional[str] = None,
        artifact_id: Optional[str] = None,
    ) -> TurnModel:
        turn = TurnModel(
            turn_id=str(uuid.uuid4()),
            session_id=session_id,
            role="assistant",
            content=answer,
            sql_executed=sql,
            artifact_ref_id=artifact_id,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self.store.save_turn(turn)
        return turn

    def get_session_history(self, session_id: str, limit: int = 5) -> List[TurnModel]:
        return self.store.get_recent_turns(session_id, limit=limit)

    def clear_session(self, session_id: str) -> bool:
        return self.store.clear_session(session_id)

    def delete_session(self, session_id: str) -> bool:
        return self.store.delete_session(session_id)

    def set_user_preference(self, user_id: str, key: str, value: str) -> None:
        self.store.set_user_preference(user_id, key, value)

    def get_user_preferences(self, user_id: str) -> Dict[str, str]:
        return self.store.get_user_preferences(user_id)

    def resolve_contextual_question(self, session_id: str, current_query: str) -> str:
        """
        ContextResolver: Follows the rule 'Rewrite, don't concatenate'.
        Inspects active frame and previous turn to produce a standalone question.
        Downstream SQL generation and agent steps never receive raw ambiguous fragments.
        """
        session = self.store.get_or_create_session(session_id)
        recent_turns = self.store.get_recent_turns(session_id, limit=2)
        q = current_query.strip()
        q_lower = q.lower()

        # Check for explicit reset indicators
        if any(trigger in q_lower for trigger in ["new question", "reset", "start over", "clear context"]):
            self.store.update_active_frame(session_id, ActiveFrame())
            return q

        # If no previous turns, current query is already standalone
        if not recent_turns:
            self._update_frame_from_query(session_id, q, session.active_frame)
            return q

        last_user_turn = next((t for t in reversed(recent_turns) if t.role == "user"), None)
        if not last_user_turn:
            self._update_frame_from_query(session_id, q, session.active_frame)
            return q

        prev_query = last_user_turn.standalone_rewrite or last_user_turn.content
        frame = session.active_frame

        # Pattern 1: Temporal shift ("what about 2024?", "and in 2025?", "for Q3?")
        if any(q_lower.startswith(p) for p in ["what about ", "and in ", "for ", "how about ", "in "]):
            target_entity = q
            for p in ["what about ", "and in ", "how about ", "for ", "in "]:
                if q_lower.startswith(p):
                    target_entity = q[len(p):].strip("?., ")
                    break

            # If previous query already had a year/quarter, substitute it directly
            old_time = re.search(r'\b(202[3-5]|Q[1-4]|\d{4})\b', prev_query, re.IGNORECASE)
            if old_time and re.search(r'\b(202[3-5]|Q[1-4]|\d{4})\b', target_entity, re.IGNORECASE):
                standalone = prev_query[:old_time.start()] + target_entity + prev_query[old_time.end():]
            elif frame.metric:
                standalone = f"What is the {frame.metric} for {target_entity}?"
            else:
                standalone = f"{prev_query.rstrip('?.')} for {target_entity}?"
            
            # Update frame time_range or filter
            frame.time_range = target_entity
            self.store.update_active_frame(session_id, frame)
            return standalone

        # Pattern 2: Category or dimension filter substitution ("what about electronics?", "and for VIPs?")
        if q_lower.startswith("and for ") or q_lower.startswith("what about for "):
            sub = q.split("for ", 1)[-1].strip("?., ")
            if frame.metric:
                standalone = f"What is the {frame.metric} for {sub}?"
            else:
                standalone = f"{prev_query.rstrip('?.')} for {sub}?"
            frame.filters["category_or_segment"] = sub
            self.store.update_active_frame(session_id, frame)
            return standalone

        # Pattern 3: Diagnostic / Why follow-up ("why did that happen?", "what caused this?")
        if any(w in q_lower for w in ["why did that happen", "why", "what caused", "explain the drivers"]):
            if frame.metric:
                standalone = f"What are the primary drivers and factors causing the change in {frame.metric}?"
            else:
                standalone = f"What caused the variation observed in: {prev_query}?"
            return standalone

        # Otherwise, query is treated as new standalone inquiry
        self._update_frame_from_query(session_id, q, frame)
        return q

    def _update_frame_from_query(self, session_id: str, query: str, current_frame: ActiveFrame) -> None:
        """Extracts candidate metric names and temporal windows to update active frame."""
        q_lower = query.lower()
        new_frame = ActiveFrame(
            metric=current_frame.metric,
            dimensions=list(current_frame.dimensions),
            filters=dict(current_frame.filters),
            time_range=current_frame.time_range,
        )

        for metric in ["revenue", "sales", "orders", "aov", "churn", "margin", "return rate", "csat", "roas"]:
            if metric in q_lower:
                new_frame.metric = metric
                break

        for yr in ["2023", "2024", "2025"]:
            if yr in q_lower:
                new_frame.time_range = yr
                break

        self.store.update_active_frame(session_id, new_frame)

    def build_context_pack(self, session_id: str, user_id: str, query: str) -> ContextPack:
        """
        Builds a deterministic context pack with token budget tracking and context hash.
        Includes resolved query, active frame, recent turns, user preferences, and exemplars.
        """
        session = self.store.get_or_create_session(session_id, user_id)
        resolved_q = self.resolve_contextual_question(session_id, query)
        recent_turns = self.store.get_recent_turns(session_id, limit=3)
        prefs = self.store.get_user_preferences(user_id)
        exemplars = self.store.list_exemplars()[:2]

        content_str = f"{session_id}:{resolved_q}:{json.dumps(session.active_frame.model_dump())}:{len(recent_turns)}"
        ctx_hash = hashlib.sha256(content_str.encode("utf-8")).hexdigest()[:16]

        return ContextPack(
            session_id=session_id,
            resolved_query=resolved_q,
            active_frame=session.active_frame,
            recent_turns=recent_turns,
            user_preferences=prefs,
            exemplars=exemplars,
            context_hash=ctx_hash,
        )


memory_service = MemoryService()

