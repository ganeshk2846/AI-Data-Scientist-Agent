"""
Pydantic contracts and data structures for shared memory and sessions.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TurnModel(BaseModel):
    turn_id: str
    session_id: str
    role: str  # "user" or "assistant"
    content: str
    standalone_rewrite: Optional[str] = None
    sql_executed: Optional[str] = None
    artifact_ref_id: Optional[str] = None
    created_at: str


class ActiveFrame(BaseModel):
    metric: Optional[str] = None
    dimensions: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    time_range: Optional[str] = None
    last_table: Optional[str] = None


class SessionModel(BaseModel):
    session_id: str
    user_id: str = "default_user"
    title: str = "New Analysis Session"
    created_at: str
    updated_at: str
    active_frame: ActiveFrame = Field(default_factory=ActiveFrame)
    turn_count: int = 0


class UserPreference(BaseModel):
    user_id: str
    pref_key: str
    pref_value: str
    updated_at: str


class ReusableExemplar(BaseModel):
    exemplar_id: str
    domain: str
    natural_question: str
    verified_sql: str
    description: str
    created_at: str


class ContextPack(BaseModel):
    session_id: str
    resolved_query: str
    active_frame: ActiveFrame
    recent_turns: List[TurnModel]
    user_preferences: Dict[str, str] = Field(default_factory=dict)
    exemplars: List[ReusableExemplar] = Field(default_factory=list)
    context_hash: str

