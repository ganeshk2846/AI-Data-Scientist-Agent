"""
FastAPI Application Entry Point for AI for BI Data Scientist Agent.
"""

from contextlib import asynccontextmanager
import time
import uuid
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from backend.app.api.v1.router import api_router
from backend.app.core.config import settings
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.errors import (
    AppException,
    app_exception_handler,
    http_exception_handler,
    validation_exception_handler,
    generic_exception_handler,
)
from backend.app.core.logging import logger
from backend.app.db.connection import check_database_readiness, verify_database_immutability


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assigns or propagates X-Request-ID for distributed tracing."""

    async def dispatch(self, request: Request, call_next):
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = req_id
        start_time = time.perf_counter()

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        return response


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifespan events."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION} [{settings.APP_ENV}]")

    # Ensure active database connection is ready
    from backend.app.db.manager import db_manager
    if not db_manager._active_adapter or not db_manager._active_adapter.is_connected:
        db_manager._load_persisted_active_database()

    # Startup verification
    db_status = check_database_readiness()
    if db_status.connected and db_status.read_only_verified:
        logger.info(
            f"Database verified (READ-ONLY): {db_status.path} "
            f"({db_status.table_count} tables, {db_status.total_rows:,} rows)"
        )
    else:
        logger.warning(f"Database readiness warning: {db_status.error}")

    if settings.is_llm_configured():
        logger.info(f"LLM Provider configured: {settings.LLM_PROVIDER}")
    else:
        logger.info(
            f"LLM Provider '{settings.LLM_PROVIDER}' running in unconfigured/offline mode. "
            "Natural language answers will use mock/fallback until credentials are provided."
        )

    yield

    logger.info(f"Shutting down {settings.APP_NAME}")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Conversational Data Scientist Agent for Business Intelligence with schema grounding and safe SQL.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware
app.add_middleware(RequestIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_origin_regex=r"^http://(localhost|127\.0\.0\.1)(:[0-9]+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(AppException, app_exception_handler)
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Routers
app.include_router(api_router)


# Root shortcut routes for standard health checks
@app.get("/health", include_in_schema=False)
async def root_health(request: Request):
    from backend.app.api.v1.endpoints.health import get_health
    return await get_health(request)


@app.get("/ready", include_in_schema=False)
async def root_ready(request: Request):
    from backend.app.api.v1.endpoints.health import get_readiness
    return await get_readiness(request)


@app.get("/", include_in_schema=False)
async def root_index():
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "online",
        "docs": "/docs",
        "api_v1": "/api/v1",
    }
