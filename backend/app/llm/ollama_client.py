"""
backend/app/llm/ollama_client.py
Native local Ollama LLM client for qwen3:4b.
Provides asynchronous, zero-mock inference with strict error reporting and latency tracking.
"""

import time
from typing import Optional
import httpx
from backend.app.core.config import settings
from backend.app.core.errors import ConfigurationError
from backend.app.core.logging import logger
from backend.app.llm.models import LLMMessage, LLMRequest, LLMResponse


class OllamaLLMProvider:
    """Production provider for local Ollama daemon hosting qwen3:4b."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
    ):
        self.base_url = (base_url or settings.OLLAMA_BASE_URL).rstrip("/")
        self.model = model or settings.OLLAMA_MODEL
        self.timeout = timeout_seconds or settings.LLM_TIMEOUT_SECONDS

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Executes real local inference via Ollama /api/chat endpoint.
        Does not fall back to mock or cloud providers.
        """
        endpoint = f"{self.base_url}/api/chat"
        messages_payload = [{"role": m.role, "content": m.content} for m in request.messages]

        payload = {
            "model": self.model,
            "messages": messages_payload,
            "stream": False,
            "options": {
                "temperature": request.temperature if request.temperature is not None else 0.0,
            },
        }

        t0 = time.perf_counter()
        eff_timeout = max(request.timeout_seconds or 0, self.timeout, 120.0)
        try:
            async with httpx.AsyncClient(timeout=eff_timeout) as client:
                res = await client.post(endpoint, json=payload)

            if res.status_code != 200:
                err_text = res.text
                logger.error(f"Ollama returned HTTP {res.status_code}: {err_text}")
                raise ConfigurationError(
                    f"Ollama request failed with HTTP {res.status_code}: {err_text}. "
                    f"Verify model '{self.model}' is installed via 'ollama run {self.model}'."
                )

            data = res.json()
            dur_ms = (time.perf_counter() - t0) * 1000

            content = data.get("message", {}).get("content", "").strip()
            total_duration_ns = data.get("total_duration", 0)
            eval_count = data.get("eval_count", 0)

            logger.info(
                f"Ollama {self.model} responded in {dur_ms:.2f}ms (eval_tokens: {eval_count})"
            )

            return LLMResponse(
                content=content,
                model=self.model,
                provider="ollama",
                tokens_used=eval_count if eval_count > 0 else None,
                finish_reason=data.get("done_reason", "stop"),
            )

        except httpx.ConnectError as e:
            logger.error(f"Failed to connect to local Ollama at {self.base_url}: {e}")
            raise ConfigurationError(
                f"Local Ollama daemon is offline or unreachable at {self.base_url}. "
                "Please run 'ollama serve' in your terminal."
            )
        except httpx.TimeoutException as e:
            logger.error(f"Ollama request timed out after {eff_timeout}s: {e}")
            raise ConfigurationError(
                f"Local Ollama inference timed out after {eff_timeout}s on model '{self.model}'."
            )
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise e
            logger.error(f"Unexpected error communicating with Ollama: {e}")
            raise ConfigurationError(f"Ollama inference error: {e}")
