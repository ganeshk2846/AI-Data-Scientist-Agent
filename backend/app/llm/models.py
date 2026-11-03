"""
Typed models for Groq LLM requests and responses.
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
    response_format: Optional[Dict[str, Any]] = None
    tools: Optional[List[Dict[str, Any]]] = None
    tool_choice: Optional[Any] = None
    stream: bool = False


class LLMResponse(BaseModel):
    content: str
    model: str
    provider: str = "groq"
    tokens_used: Optional[int] = None
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    raw_response: Optional[Dict[str, Any]] = None
