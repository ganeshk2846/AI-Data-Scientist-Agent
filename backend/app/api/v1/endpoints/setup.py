"""
API endpoints for system setup readiness, step-by-step onboarding guard, and preparation recovery.
Enforces the requirement that the chat workspace unlocks ONLY when LLM, database, and schema preparation
are fully verified.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.contracts import ConnectionStatus
from backend.app.core.models import APIResponse
from backend.app.db.manager import db_manager
from backend.app.llm.client import load_persisted_llm_credentials, mask_api_key
from backend.app.schema.job import job_manager
from backend.app.schema.models import JobStatusEnum, PreparationJobState
from backend.app.schema.service import schema_service

router = APIRouter(prefix="/setup", tags=["Setup & Onboarding"])


class SetupLLMInfo(BaseModel):
    provider: str = "groq"
    model: str
    masked_key: Optional[str] = None
    connected: bool = False


class SetupDatabaseInfo(BaseModel):
    name: str
    engine: str
    read_only: bool = True
    table_count: int = 0
    fingerprint: Optional[str] = None
    connected: bool = False


class SetupStatusResponse(BaseModel):
    llm_status: str  # "CONNECTED" | "NOT_CONNECTED"
    database_status: str  # "CONNECTED" | "NOT_CONNECTED"
    preparation_status: str  # "COMPLETED" | "RUNNING" | "FAILED" | "NOT_STARTED"
    chat_ready: bool = False
    llm: SetupLLMInfo
    database: Optional[SetupDatabaseInfo] = None
    preparation: Optional[Dict[str, Any]] = None


@router.get(
    "/status",
    response_model=APIResponse[SetupStatusResponse],
    summary="Get unified self-service setup readiness status",
)
async def get_setup_status(request: Request) -> APIResponse[SetupStatusResponse]:
    """
    Evaluates backend setup readiness:
    - llm_status: Is Groq API key configured and verified?
    - database_status: Is a database currently connected in read-only mode?
    - preparation_status: Is schema indexing complete for the active database fingerprint?
    - chat_ready: True ONLY when all three requirements are met.
    """
    request_id = getattr(request.state, "request_id", None)

    # 1. Derive LLM Status
    is_llm_ready = settings.is_llm_configured()
    active_key = settings.GROQ_API_KEY
    active_model = settings.GROQ_MODEL

    if not is_llm_ready:
        persisted = load_persisted_llm_credentials()
        if persisted:
            is_llm_ready = True
            active_key = persisted.get("api_key")
            active_model = persisted.get("model", active_model)

    llm_info = SetupLLMInfo(
        provider="groq",
        model=active_model,
        masked_key=mask_api_key(active_key) if is_llm_ready else None,
        connected=is_llm_ready,
    )
    llm_status_str = "CONNECTED" if is_llm_ready else "NOT_CONNECTED"

    # 2. Derive Database Status
    db_config = db_manager.get_active_config()
    is_db_connected = False
    db_info: Optional[SetupDatabaseInfo] = None
    active_fp: Optional[str] = None

    if db_config and db_config.status != ConnectionStatus.DISCONNECTED:
        try:
            adapter = db_manager.get_active_adapter()
            is_db_connected = adapter.is_connected
            active_fp = adapter.compute_fingerprint()
            table_count = len(adapter.get_table_names())
            db_info = SetupDatabaseInfo(
                name=db_config.name,
                engine=db_config.engine.value,
                read_only=db_config.read_only,
                table_count=table_count,
                fingerprint=active_fp,
                connected=is_db_connected,
            )
        except Exception:
            is_db_connected = False
            active_fp = db_config.fingerprint
            db_info = SetupDatabaseInfo(
                name=db_config.name,
                engine=db_config.engine.value,
                read_only=db_config.read_only,
                table_count=0,
                fingerprint=active_fp,
                connected=False,
            )

    database_status_str = "CONNECTED" if is_db_connected else "NOT_CONNECTED"

    # 3. Derive Preparation Status
    prep_status_str = "NOT_STARTED"
    latest_job = job_manager.get_latest_job()
    prep_data: Optional[Dict[str, Any]] = None

    if latest_job:
        prep_data = latest_job.model_dump()
        if latest_job.status == JobStatusEnum.RUNNING or latest_job.status == JobStatusEnum.PENDING:
            prep_status_str = "RUNNING"
        elif latest_job.status == JobStatusEnum.FAILED:
            prep_status_str = "FAILED"
        elif latest_job.status == JobStatusEnum.SUCCEEDED:
            if is_db_connected and active_fp and latest_job.source_fingerprint == active_fp:
                prep_status_str = "COMPLETED"
            elif not is_db_connected:
                prep_status_str = "NOT_STARTED"
            else:
                prep_status_str = "NOT_STARTED"

    # Check cached catalog if no job was executed in this process lifetime
    if prep_status_str == "NOT_STARTED" and is_db_connected and active_fp:
        cached_cat = schema_service.get_cached_catalog()
        if cached_cat and cached_cat.source_fingerprint == active_fp:
            prep_status_str = "COMPLETED"
            prep_data = {
                "job_id": "cached_fingerprint",
                "status": "succeeded",
                "progress_percent": 100,
                "message": f"Verified cached catalog for {cached_cat.total_tables} tables.",
                "total_tables": cached_cat.total_tables,
                "tables_processed": cached_cat.total_tables,
                "source_fingerprint": active_fp,
            }

    # 4. Derive Chat Readiness
    chat_ready = (
        llm_status_str == "CONNECTED"
        and database_status_str == "CONNECTED"
        and prep_status_str == "COMPLETED"
    )

    data = SetupStatusResponse(
        llm_status=llm_status_str,
        database_status=database_status_str,
        preparation_status=prep_status_str,
        chat_ready=chat_ready,
        llm=llm_info,
        database=db_info,
        preparation=prep_data,
    )
    return APIResponse(success=True, data=data, request_id=request_id)


@router.post(
    "/retry-preparation",
    response_model=APIResponse[PreparationJobState],
    summary="Retry schema preparation job",
)
async def retry_preparation(request: Request) -> APIResponse[PreparationJobState]:
    """Forces retry of schema preparation for the active database."""
    request_id = getattr(request.state, "request_id", None)
    job = await job_manager.retry_preparation_job()
    return APIResponse(success=True, data=job, request_id=request_id)
