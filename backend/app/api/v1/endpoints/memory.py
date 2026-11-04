"""
REST API endpoints for shared conversational memory, sessions, and preferences.
"""

from typing import Any, Dict, List, Optional, Set
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from backend.app.core.models import APIResponse
from backend.app.memory.models import ReusableExemplar, SessionModel, TurnModel
from backend.app.memory.service import memory_service

router = APIRouter(prefix="/memory", tags=["Shared Memory & Sessions"])


class PreferencePayload(BaseModel):
    pref_key: str = Field(..., min_length=1, max_length=100)
    pref_value: str = Field(..., max_length=500)


class CreateSessionPayload(BaseModel):
    title: Optional[str] = None
    user_id: str = "default_user"


class SessionDetailPayload(BaseModel):
    session: SessionModel
    turns: List[TurnModel]


@router.get(
    "/sessions",
    response_model=APIResponse[List[SessionModel]],
    summary="List all user conversation sessions",
)
async def list_sessions(request: Request, user_id: str = "default_user") -> APIResponse[List[SessionModel]]:
    request_id = getattr(request.state, "request_id", None)
    sessions = memory_service.list_sessions(user_id=user_id)
    return APIResponse(success=True, data=sessions, request_id=request_id)


@router.get(
    "/sessions/{session_id}",
    response_model=APIResponse[SessionDetailPayload],
    summary="Get session details and recent turns",
)
async def get_session(session_id: str, request: Request) -> APIResponse[SessionDetailPayload]:
    request_id = getattr(request.state, "request_id", None)
    session = memory_service.get_or_create_session(session_id)
    turns = memory_service.get_session_history(session_id, limit=20)
    payload = SessionDetailPayload(session=session, turns=turns)
    return APIResponse(success=True, data=payload, request_id=request_id)


@router.post(
    "/sessions/{session_id}/clear",
    response_model=APIResponse[Dict[str, Any]],
    summary="Clear all turns and reset frame for a session",
)
async def clear_session(session_id: str, request: Request) -> APIResponse[Dict[str, Any]]:
    request_id = getattr(request.state, "request_id", None)
    cleared = memory_service.clear_session(session_id)
    try:
        from backend.app.orchestration.supervisor import agentic_supervisor
        agentic_supervisor.clear_session(session_id)
        from backend.app.analysis.orchestrator import analytical_orchestrator
        analytical_orchestrator.clear_session(session_id)
    except Exception as _e:
        pass
    return APIResponse(
        success=cleared,
        data={"session_id": session_id, "cleared": cleared},
        request_id=request_id,
    )


@router.delete(
    "/sessions/{session_id}",
    response_model=APIResponse[Dict[str, Any]],
    summary="Permanently delete a session container and its history",
)
async def delete_session(session_id: str, request: Request) -> APIResponse[Dict[str, Any]]:
    request_id = getattr(request.state, "request_id", None)
    deleted = memory_service.delete_session(session_id)
    try:
        from backend.app.orchestration.supervisor import agentic_supervisor
        agentic_supervisor.clear_session(session_id)
        from backend.app.analysis.orchestrator import analytical_orchestrator
        analytical_orchestrator.clear_session(session_id)
    except Exception as _e:
        pass
    return APIResponse(
        success=deleted,
        data={"session_id": session_id, "deleted": deleted},
        request_id=request_id,
    )


@router.get(
    "/preferences",
    response_model=APIResponse[Dict[str, str]],
    summary="Get user preferences",
)
async def get_preferences(request: Request, user_id: str = "default_user") -> APIResponse[Dict[str, str]]:
    request_id = getattr(request.state, "request_id", None)
    prefs = memory_service.get_user_preferences(user_id=user_id)
    return APIResponse(success=True, data=prefs, request_id=request_id)


@router.post(
    "/preferences",
    response_model=APIResponse[Dict[str, str]],
    summary="Set a user preference",
)
async def set_preference(
    body: PreferencePayload,
    request: Request,
    user_id: str = "default_user",
) -> APIResponse[Dict[str, str]]:
    request_id = getattr(request.state, "request_id", None)
    memory_service.set_user_preference(user_id=user_id, key=body.pref_key, value=body.pref_value)
    prefs = memory_service.get_user_preferences(user_id=user_id)
    return APIResponse(success=True, data=prefs, request_id=request_id)


@router.get(
    "/exemplars",
    response_model=APIResponse[List[ReusableExemplar]],
    summary="List verified reusable SQL exemplars",
)
async def list_exemplars(request: Request, domain: Optional[str] = None) -> APIResponse[List[ReusableExemplar]]:
    request_id = getattr(request.state, "request_id", None)
    exemplars = memory_service.store.list_exemplars(domain=domain)
    return APIResponse(success=True, data=exemplars, request_id=request_id)

