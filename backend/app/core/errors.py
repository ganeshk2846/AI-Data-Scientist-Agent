"""
Application exceptions and standardized error handlers.
"""

from typing import Any, Dict, Optional
from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException
from backend.app.core.models import APIResponse, ErrorDetail


class AppException(Exception):
    """Base application exception."""
    def __init__(
        self,
        message: str,
        code: str = "INTERNAL_SERVER_ERROR",
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: Optional[Dict[str, Any]] = None,
    ):
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}


class DatabaseError(AppException):
    """Database connection or query execution failure."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="DATABASE_ERROR",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            details=details,
        )


class DatabaseReadOnlyViolationError(AppException):
    """Violation of read-only database guarantee."""
    def __init__(self, message: str = "Attempted write operation on read-only database."):
        super().__init__(
            message=message,
            code="DATABASE_READ_ONLY_VIOLATION",
            status_code=status.HTTP_403_FORBIDDEN,
        )


class ConfigurationError(AppException):
    """Missing or invalid configuration setting."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="CONFIGURATION_ERROR",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            details=details,
        )


class ResourceNotFoundError(AppException):
    """Requested resource was not found."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="RESOURCE_NOT_FOUND",
            status_code=status.HTTP_404_NOT_FOUND,
            details=details,
        )


class ValidationError(AppException):
    """Request or payload validation failed."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            code="VALIDATION_ERROR",
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            details=details,
        )


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handles all domain AppException instances."""
    request_id = getattr(request.state, "request_id", None)
    error = ErrorDetail(
        code=exc.code,
        message=exc.message,
        details=exc.details,
    )
    envelope = APIResponse[None](
        success=False,
        data=None,
        error=error,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))


async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Handles standard HTTP exceptions (e.g. 404, 405)."""
    request_id = getattr(request.state, "request_id", None)
    code = "RESOURCE_NOT_FOUND" if exc.status_code == 404 else f"HTTP_{exc.status_code}"
    error = ErrorDetail(
        code=code,
        message=str(exc.detail),
        details={"status_code": exc.status_code},
    )
    envelope = APIResponse[None](
        success=False,
        data=None,
        error=error,
        request_id=request_id,
    )
    return JSONResponse(status_code=exc.status_code, content=envelope.model_dump(mode="json"))


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Handles Pydantic request validation errors."""
    request_id = getattr(request.state, "request_id", None)
    error = ErrorDetail(
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        details={"validation_errors": exc.errors()},
    )
    envelope = APIResponse[None](
        success=False,
        data=None,
        error=error,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content=envelope.model_dump(mode="json"),
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Fallback handler for unhandled exceptions."""
    request_id = getattr(request.state, "request_id", None)
    error = ErrorDetail(
        code="INTERNAL_SERVER_ERROR",
        message="An unexpected server error occurred.",
        details={"error_type": type(exc).__name__},
    )
    envelope = APIResponse[None](
        success=False,
        data=None,
        error=error,
        request_id=request_id,
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=envelope.model_dump(mode="json"),
    )
