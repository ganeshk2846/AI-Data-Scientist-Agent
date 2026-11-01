"""
Pydantic v2 data models for API response envelopes, error models, and system health status.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Generic, List, Optional, TypeVar
from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorDetail(BaseModel):
    """Structured error representation."""
    code: str = Field(..., description="Machine-readable error code")
    message: str = Field(..., description="Human-readable explanation of error")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Contextual debugging details")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class APIResponse(BaseModel, Generic[T]):
    """Standardized top-level API response envelope."""
    success: bool = Field(..., description="Whether the request succeeded")
    data: Optional[T] = Field(default=None, description="Payload data if successful")
    error: Optional[ErrorDetail] = Field(default=None, description="Error detail if failed")
    request_id: Optional[str] = Field(default=None, description="Correlated trace request ID")


class HealthStatus(BaseModel):
    """Basic health check status."""
    status: str = "ok"
    version: str
    environment: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DatabaseReadiness(BaseModel):
    """Database connectivity and read-only verification."""
    connected: bool
    read_only_verified: bool
    path: str
    size_bytes: Optional[int] = None
    table_count: Optional[int] = None
    total_rows: Optional[int] = None
    error: Optional[str] = None


class LLMReadiness(BaseModel):
    """LLM provider configuration status."""
    provider: str
    configured: bool
    model: str
    message: str


class ReadinessStatus(BaseModel):
    """Comprehensive readiness status for backend dependencies."""
    ready: bool
    database: DatabaseReadiness
    llm: LLMReadiness
    app_store_ready: bool
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
