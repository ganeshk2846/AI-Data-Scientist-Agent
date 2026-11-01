"""
Typed models for provider-agnostic LLM requests and responses.
"""

from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field


class LLMMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str


class LLMRequest(BaseModel):
    messages: List[LLMMessage]
    temperature: float = 0.0
    max_tokens: int = 1500
    timeout_seconds: int = 45


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str
    tokens_used: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None

