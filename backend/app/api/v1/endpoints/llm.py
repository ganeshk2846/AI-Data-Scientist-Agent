"""
API endpoints for Groq LLM connection, model discovery, and lifecycle management.
Groq is the ONLY supported LLM provider across the entire application.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request, status
from openai import AsyncOpenAI, AuthenticationError
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.models import APIResponse
from backend.app.llm.client import (
    SUPPORTED_GROQ_MODELS,
    disconnect_groq_credentials,
    get_llm_provider,
    load_persisted_llm_credentials,
    mask_api_key,
    set_active_groq_credentials,
)

router = APIRouter(prefix="/llm", tags=["LLM Connection"])


class LLMConnectRequest(BaseModel):
    api_key: str = Field(..., min_length=1, description="Groq API key (starts with gsk_)")
    model: str = Field(default="llama-3.3-70b-versatile", description="Supported Groq model ID")


class LLMModelInfo(BaseModel):
    id: str
    name: str
    context_window: int
    is_recommended: bool
    description: str


class LLMStatusData(BaseModel):
    connected: bool
    provider: str = "groq"
    model: str
    masked_key: Optional[str] = None
    status: str  # "CONNECTED" | "NOT_CONNECTED"


@router.get(
    "/status",
    response_model=APIResponse[LLMStatusData],
    summary="Get current Groq LLM connection status",
)
async def get_llm_status(request: Request) -> APIResponse[LLMStatusData]:
    """Returns the masked Groq connection status and active model."""
    request_id = getattr(request.state, "request_id", None)

    # Check settings or persisted store
    is_configured = settings.is_llm_configured()
    active_key = settings.GROQ_API_KEY
    active_model = settings.GROQ_MODEL

    if not is_configured:
        persisted = load_persisted_llm_credentials()
        if persisted:
            is_configured = True
            active_key = persisted.get("api_key")
            active_model = persisted.get("model", active_model)

    data = LLMStatusData(
        connected=is_configured,
        provider="groq",
        model=active_model,
        masked_key=mask_api_key(active_key) if is_configured else None,
        status="CONNECTED" if is_configured else "NOT_CONNECTED",
    )
    return APIResponse(success=True, data=data, request_id=request_id)


@router.get(
    "/models",
    response_model=APIResponse[List[LLMModelInfo]],
    summary="List supported Groq models",
)
async def list_models(request: Request) -> APIResponse[List[LLMModelInfo]]:
    """Returns list of supported and validated Groq models."""
    request_id = getattr(request.state, "request_id", None)
    models = [LLMModelInfo(**m) for m in SUPPORTED_GROQ_MODELS]
    return APIResponse(success=True, data=models, request_id=request_id)


@router.post(
    "/connect",
    response_model=APIResponse[LLMStatusData],
    summary="Validate and connect Groq API key",
)
async def connect_llm(req: LLMConnectRequest, request: Request) -> APIResponse[LLMStatusData]:
    """
    Validates the provided Groq API key with an actual Groq API call,
    persists the encrypted credential, and establishes the connection.
    Never logs or exposes the raw key.
    """
    request_id = getattr(request.state, "request_id", None)
    clean_key = req.api_key.strip()
    if not clean_key:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Groq API key cannot be empty.",
        )

    # Check test placeholder or mock testing
    is_mock_test = settings.APP_ENV == "testing" and (
        clean_key.startswith("mock_")
        or clean_key.startswith("test_")
        or clean_key in ["gsk_test_placeholder"]
    )

    if not is_mock_test:
        # Validate against live Groq API
        test_client = AsyncOpenAI(
            api_key=clean_key,
            base_url=settings.GROQ_BASE_URL.rstrip("/"),
            timeout=10.0,
        )
        try:
            # Query models endpoint to verify key authenticity
            await test_client.models.list()
        except AuthenticationError as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid Groq API key: {str(e)}",
            )
        except Exception as e:
            err_msg = str(e)
            if "invalid_api_key" in err_msg.lower() or "unauthorized" in err_msg.lower() or "401" in err_msg:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Authentication failed: {err_msg}",
                )
            # If network error or timeout, return descriptive error
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Failed to communicate with Groq API: {err_msg}",
            )

    # Update in-memory credentials and persist encrypted configuration
    set_active_groq_credentials(clean_key, req.model)

    data = LLMStatusData(
        connected=True,
        provider="groq",
        model=req.model,
        masked_key=mask_api_key(clean_key),
        status="CONNECTED",
    )
    return APIResponse(success=True, data=data, request_id=request_id)


@router.post(
    "/disconnect",
    response_model=APIResponse[Dict[str, str]],
    summary="Disconnect Groq LLM",
)
async def disconnect_llm(request: Request) -> APIResponse[Dict[str, str]]:
    """Clears active Groq credentials from runtime memory and persistent store."""
    request_id = getattr(request.state, "request_id", None)
    disconnect_groq_credentials()
    return APIResponse(
        success=True,
        data={"message": "Groq LLM connection disconnected."},
        request_id=request_id,
    )
