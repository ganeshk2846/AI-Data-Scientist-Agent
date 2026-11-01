"""
System health and readiness endpoints.
"""

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from backend.app.core.config import settings
from backend.app.core.models import (
    APIResponse,
    HealthStatus,
    LLMReadiness,
    ReadinessStatus,
)
from backend.app.db.connection import check_database_readiness

router = APIRouter(tags=["System & Health"])


@router.get("/health", response_model=APIResponse[HealthStatus], summary="Basic service health probe")
async def get_health(request: Request) -> APIResponse[HealthStatus]:
    """Returns basic service liveness and version information."""
    request_id = getattr(request.state, "request_id", None)
    payload = HealthStatus(
        status="ok",
        version=settings.APP_VERSION,
        environment=settings.APP_ENV,
    )
    return APIResponse(success=True, data=payload, request_id=request_id)


@router.get("/ready", response_model=APIResponse[ReadinessStatus], summary="Comprehensive readiness probe")
async def get_readiness(request: Request) -> JSONResponse:
    """
    Evaluates backend dependencies including:
    - Read-only connectivity to ecommerce.sqlite
    - LLM provider configuration status (non-blocking if unconfigured)
    - Writable application store state
    """
    request_id = getattr(request.state, "request_id", None)
    db_readiness = check_database_readiness()

    llm_configured = settings.is_llm_configured()
    if llm_configured:
        llm_msg = f"Provider '{settings.LLM_PROVIDER}' is configured and ready."
    else:
        llm_msg = (
            f"Provider '{settings.LLM_PROVIDER}' API key is not configured. "
            "Natural language SQL synthesis requires configuring API credentials in .env, "
            "or running in mock mode."
        )

    llm_status = LLMReadiness(
        provider=settings.LLM_PROVIDER,
        configured=llm_configured,
        model=getattr(settings, f"{settings.LLM_PROVIDER.upper()}_MODEL", "default") if settings.LLM_PROVIDER != "mock" else "mock-v1",
        message=llm_msg,
    )

    # Agent app store directory readiness (parent folder must exist and be writable)
    app_store_ready = settings.resolved_app_db_path.parent.exists()

    overall_ready = db_readiness.connected and db_readiness.read_only_verified and app_store_ready

    payload = ReadinessStatus(
        ready=overall_ready,
        database=db_readiness,
        llm=llm_status,
        app_store_ready=app_store_ready,
        version=settings.APP_VERSION,
    )

    envelope = APIResponse(
        success=overall_ready,
        data=payload,
        request_id=request_id,
    )

    http_status = status.HTTP_200_OK if overall_ready else status.HTTP_503_SERVICE_UNAVAILABLE
    return JSONResponse(status_code=http_status, content=envelope.model_dump(mode="json"))


@router.get("/system/status", response_model=APIResponse[dict], summary="Detailed system configuration and status")
async def get_system_status(request: Request) -> APIResponse[dict]:
    """Returns safe diagnostic system metadata and configuration."""
    request_id = getattr(request.state, "request_id", None)
    data = {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "environment": settings.APP_ENV,
            "debug": settings.APP_DEBUG,
        },
        "database": check_database_readiness().model_dump(),
        "llm_provider": {
            "provider": settings.LLM_PROVIDER,
            "configured": settings.is_llm_configured(),
        },
        "limits": {
            "sql_query_timeout_seconds": settings.SQL_QUERY_TIMEOUT_SECONDS,
            "sql_max_rows_return": settings.SQL_MAX_ROWS_RETURN,
            "llm_timeout_seconds": settings.LLM_TIMEOUT_SECONDS,
        },
    }
    return APIResponse(success=True, data=data, request_id=request_id)

