"""
Dedicated single-provider LLM interface supporting Groq Cloud API.
Groq uses an OpenAI-compatible Chat Completions API with ultra-fast inference.
Deterministic mock implementation is strictly reserved for automated testing.
"""

from abc import ABC, abstractmethod
import asyncio
import os
import re
from typing import Any, AsyncIterator, Dict, List, Optional
import openai
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AsyncOpenAI,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

from backend.app.core.config import settings
from backend.app.core.errors import ConfigurationError
from backend.app.core.logging import logger
from backend.app.llm.models import LLMMessage, LLMRequest, LLMResponse

_UNSET = object()


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates a text completion for the provided messages."""
        pass

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[str]:
        """Streams text chunks for the provided messages."""
        response = await self.generate(request)
        yield response.content


class GroqLLMProvider(BaseLLMProvider):
    """
    Production single-provider client for Groq API using OpenAI-compatible endpoints.
    Base URL: https://api.groq.com/openai/v1
    Strictly zero fallback to mock or other cloud providers in production runtime.
    """

    def __init__(
        self,
        api_key: Any = _UNSET,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout_seconds: Optional[int] = None,
        max_retries: int = 2,
    ):
        if api_key is _UNSET:
            self.api_key = settings.GROQ_API_KEY
        else:
            self.api_key = api_key

        self.model = model or settings.GROQ_MODEL
        self.base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self.timeout_seconds = timeout_seconds or settings.LLM_TIMEOUT_SECONDS
        self.max_retries = max_retries

        self._client: Optional[AsyncOpenAI] = None
        if self._is_valid_key(self.api_key):
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=float(self.timeout_seconds),
            )

    @staticmethod
    def _is_valid_key(key: Optional[str]) -> bool:
        if not key:
            return False
        clean = key.strip()
        return bool(clean and not clean.startswith("your_") and clean != "gsk_test_placeholder")

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            if not self._is_valid_key(self.api_key):
                raise ConfigurationError(
                    "GROQ_API_KEY is not configured or contains placeholder value. "
                    "Set a valid Groq API key in the backend .env file to enable Groq LLM inference."
                )
            self._client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
                timeout=float(self.timeout_seconds),
            )
        return self._client

    async def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Executes asynchronous chat completion with Groq API.
        Includes bounded retry handling for transient rate-limit (429) and server (503) errors.
        """
        active_client = self.client  # raises ConfigurationError if key is missing

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "timeout": float(request.timeout_seconds or self.timeout_seconds),
        }
        if request.response_format:
            kwargs["response_format"] = request.response_format
        if request.tools:
            kwargs["tools"] = request.tools
        if request.tool_choice:
            kwargs["tool_choice"] = request.tool_choice

        retries = 0
        backoff = 1.0
        while True:
            try:
                res = await active_client.chat.completions.create(**kwargs)
                choice = res.choices[0]
                message = choice.message
                content = message.content or ""
                finish_reason = choice.finish_reason

                tool_calls = None
                if getattr(message, "tool_calls", None):
                    tool_calls = [
                        tc.model_dump() if hasattr(tc, "model_dump") else dict(tc)
                        for tc in message.tool_calls
                    ]

                tokens_used = res.usage.total_tokens if res.usage else None
                prompt_tokens = res.usage.prompt_tokens if res.usage else None
                completion_tokens = res.usage.completion_tokens if res.usage else None

                return LLMResponse(
                    content=content,
                    model=self.model,
                    provider="groq",
                    tokens_used=tokens_used,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    finish_reason=finish_reason,
                    tool_calls=tool_calls,
                )
            except AuthenticationError as e:
                logger.error(f"Groq API authentication failed: {e}")
                raise ConfigurationError(
                    f"Groq authentication failed (HTTP 401). Please verify your GROQ_API_KEY in .env."
                ) from e
            except NotFoundError as e:
                logger.error(f"Groq model or resource not found: {e}")
                raise ConfigurationError(
                    f"Groq model '{self.model}' not found (HTTP 404). Please verify GROQ_MODEL in .env."
                ) from e
            except RateLimitError as e:
                if retries < self.max_retries:
                    retries += 1
                    logger.warning(
                        f"Groq rate limit (429) encountered. Retrying in {backoff}s (attempt {retries}/{self.max_retries})..."
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                logger.error(f"Groq rate limit exceeded after {self.max_retries} retries: {e}")
                raise ConfigurationError(
                    f"Groq API rate limit exceeded after {self.max_retries} retries. Please retry later or upgrade tier."
                ) from e
            except APITimeoutError as e:
                logger.error(f"Groq API request timed out: {e}")
                raise ConfigurationError(
                    f"Groq API request timed out after {request.timeout_seconds or self.timeout_seconds}s."
                ) from e
            except APIConnectionError as e:
                logger.error(f"Failed to connect to Groq API at {self.base_url}: {e}")
                raise ConfigurationError(
                    f"Failed to connect to Groq API endpoint '{self.base_url}'. Check network connectivity."
                ) from e
            except APIStatusError as e:
                if e.status_code == 503 and retries < self.max_retries:
                    retries += 1
                    logger.warning(
                        f"Groq service unavailable (503). Retrying in {backoff}s (attempt {retries}/{self.max_retries})..."
                    )
                    await asyncio.sleep(backoff)
                    backoff *= 2.0
                    continue
                logger.error(f"Groq API error HTTP {e.status_code}: {e.message}")
                raise ConfigurationError(
                    f"Groq API request failed with HTTP {e.status_code}: {e.message}"
                ) from e
            except Exception as e:
                if isinstance(e, ConfigurationError):
                    raise
                logger.error(f"Unexpected error communicating with Groq: {e}")
                raise ConfigurationError(f"Unexpected Groq inference error: {e}") from e

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[str]:
        """
        Streams completions token-by-token from Groq API.
        """
        active_client = self.client  # raises ConfigurationError if key is missing

        messages = [{"role": m.role, "content": m.content} for m in request.messages]
        kwargs: Dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "stream": True,
            "timeout": float(request.timeout_seconds or self.timeout_seconds),
        }
        if request.response_format:
            kwargs["response_format"] = request.response_format

        try:
            stream = await active_client.chat.completions.create(**kwargs)
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except AuthenticationError as e:
            logger.error(f"Groq streaming authentication failed: {e}")
            raise ConfigurationError(
                "Groq authentication failed (HTTP 401). Please verify your GROQ_API_KEY in .env."
            ) from e
        except NotFoundError as e:
            logger.error(f"Groq model not found for streaming: {e}")
            raise ConfigurationError(
                f"Groq model '{self.model}' not found (HTTP 404). Please verify GROQ_MODEL in .env."
            ) from e
        except RateLimitError as e:
            logger.error(f"Groq streaming rate limit hit: {e}")
            raise ConfigurationError("Groq API rate limit exceeded during streaming.") from e
        except APITimeoutError as e:
            logger.error(f"Groq streaming timed out: {e}")
            raise ConfigurationError("Groq streaming request timed out.") from e
        except APIConnectionError as e:
            logger.error(f"Groq streaming connection error: {e}")
            raise ConfigurationError(f"Failed to connect to Groq API endpoint '{self.base_url}'.") from e
        except Exception as e:
            if isinstance(e, ConfigurationError):
                raise
            logger.error(f"Groq streaming error: {e}")
            raise ConfigurationError(f"Groq streaming error: {e}") from e


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, schema-grounded Mock LLM strictly for offline automated testing.
    Never used as a silent fallback for production Groq inference.
    """

    async def generate(self, request: LLMRequest) -> LLMResponse:
        system_message = ""
        user_message = ""
        for m in request.messages:
            if m.role == "system":
                system_message += " " + m.content.lower()
            elif m.role == "user":
                user_message += " " + m.content.lower()

        combined = (system_message + " " + user_message).lower()

        # Check if prompt is asking for SQL generation
        if "sql" in system_message or "generate sql" in combined or "select query" in combined or "sqlite select" in combined:
            sql = self._generate_grounded_sql(user_message)
            return LLMResponse(
                content=f"```sql\n{sql}\n```",
                model="mock-grounded-v1",
                provider="mock",
                tokens_used=120,
            )

        # Check if prompt is asking for Router classification:
        if "classify" in system_message or "router" in system_message:
            intent = self._classify_intent(user_message)
            return LLMResponse(
                content=f'{{"intent": "{intent}", "confidence": 0.95, "complexity": "simple", "reasoning": "Mock classification based on keywords.", "target_domains": ["Orders & Transactions"], "suggested_entities": ["orders"]}}',
                model="mock-router-v1",
                provider="mock",
                tokens_used=40,
            )

        # General explanation or summary:
        return LLMResponse(
            content="### Direct Answer\n\nTotal sales and order metrics show healthy operational activity with verified records across the connected SQLite warehouse.\n\n### Key Findings\n- Total recorded transaction volumes match verified database rows.\n- Revenue figures align with delivered and paid order reconciliations.",
            model="mock-v1",
            provider="mock",
            tokens_used=50,
        )

    async def stream_generate(self, request: LLMRequest) -> AsyncIterator[str]:
        response = await self.generate(request)
        for word in response.content.split(" "):
            yield word + " "

    def _classify_intent(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if any(w in prompt_lower for w in ["should", "recommend", "optimize", "prescriptive"]):
            return "prescriptive"
        elif any(w in prompt_lower for w in ["forecast", "predict", "next month", "future", "predictive"]):
            return "predictive"
        elif any(w in prompt_lower for w in ["why", "driver", "cause", "drop", "spike", "diagnostic"]):
            return "diagnostic"
        elif any(w in prompt_lower for w in ["compare", "versus", "vs", "difference", "comparative"]):
            return "comparative"
        elif any(w in prompt_lower for w in ["trend", "over time", "monthly", "daily", "growth"]):
            return "trend"
        return "descriptive"

    def _generate_grounded_sql(self, prompt: str) -> str:
        """Emits valid, verified SQL against real tables in ecommerce.sqlite."""
        year_match = re.search(r'(?:^|\D)(202[0-9])(?:\D|$)', prompt)
        target_year = year_match.group(1) if year_match else None

        if "order" in prompt and "status" in prompt:
            return "SELECT order_status, COUNT(*) AS order_count, ROUND(SUM(total_amount), 2) AS total_value FROM orders GROUP BY order_status ORDER BY order_count DESC;"
        elif "churn" in prompt or ("segment" in prompt and "risk" in prompt):
            return "SELECT cs.segment_name, COUNT(DISTINCT csh.customer_id) AS customers_at_risk, ROUND(SUM(o.total_amount), 2) AS revenue_at_risk FROM customer_segments cs JOIN customer_segment_history csh ON cs.segment_id = csh.segment_id JOIN customers c ON csh.customer_id = c.customer_id LEFT JOIN orders o ON c.customer_id = o.customer_id WHERE cs.segment_name = 'At Risk' AND (csh.valid_to IS NULL OR csh.valid_to >= DATETIME('now')) GROUP BY cs.segment_name;"
        elif "segment" in prompt or "customer" in prompt:
            return "SELECT cs.segment_name, COUNT(DISTINCT csh.customer_id) AS customer_count FROM customer_segments cs JOIN customer_segment_history csh ON cs.segment_id = csh.segment_id WHERE csh.valid_to IS NULL GROUP BY cs.segment_name ORDER BY customer_count DESC;"
        elif "top" in prompt and "categor" in prompt:
            return "SELECT c.category_name, ROUND(SUM(oi.subtotal), 2) AS category_revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN categories c ON p.category_id = c.category_id GROUP BY c.category_name ORDER BY category_revenue DESC LIMIT 5;"
        elif target_year and ("revenue" in prompt or "sales" in prompt):
            return f"SELECT strftime('%Y', order_date) AS order_year, ROUND(SUM(total_amount), 2) AS total_revenue FROM orders WHERE strftime('%Y', order_date) = '{target_year}' AND order_status = 'delivered';"
        elif "revenue" in prompt or "sales" in prompt:
            return "SELECT strftime('%Y', order_date) AS year, COUNT(order_id) AS total_orders, ROUND(SUM(total_amount), 2) AS total_revenue FROM orders WHERE order_status = 'delivered' GROUP BY year ORDER BY year ASC;"
        elif "payment" in prompt:
            return "SELECT payment_method, payment_status, COUNT(*) AS count, ROUND(SUM(amount), 2) AS total_amount FROM payments GROUP BY payment_method, payment_status ORDER BY total_amount DESC;"
        elif "channel" in prompt or "marketing" in prompt:
            return "SELECT mc.channel_name, ROUND(SUM(ms.spend_amount), 2) AS total_spend FROM marketing_spend ms JOIN marketing_channels mc ON ms.channel_id = mc.channel_id GROUP BY mc.channel_name ORDER BY total_spend DESC;"
        else:
            return "SELECT order_status, COUNT(*) AS order_count, ROUND(SUM(total_amount), 2) AS total_amount FROM orders GROUP BY order_status;"


SUPPORTED_GROQ_MODELS = [
    {
        "id": "openai/gpt-oss-120b",
        "name": "GPT-OSS 120B",
        "context_window": 8192,
        "is_recommended": True,
        "description": "High parameter open weights model with strong structured outputs (Recommended)",
    },
    {
        "id": "qwen/qwen3.8-27b",
        "name": "Qwen 3.8 27B",
        "context_window": 32768,
        "is_recommended": False,
        "description": "Ultra low latency 27B model optimized for fast query synthesis",
    },
    {
        "id": "llama-3.3-70b-versatile",
        "name": "Llama 3.3 70B Versatile",
        "context_window": 128000,
        "is_recommended": False,
        "description": "High performance, excellent reasoning and SQL synthesis capabilities",
    },
    {
        "id": "llama-3.1-8b-instant",
        "name": "Llama 3.1 8B Instant",
        "context_window": 128000,
        "is_recommended": False,
        "description": "Ultra low latency inference optimized for high-throughput descriptive exploration",
    },
    {
        "id": "llama3-70b-8192",
        "name": "Llama 3 70B",
        "context_window": 8192,
        "is_recommended": False,
        "description": "Versatile reasoning model with 8k context window",
    },
    {
        "id": "mixtral-8x7b-32768",
        "name": "Mixtral 8x7B 32k",
        "context_window": 32768,
        "is_recommended": False,
        "description": "MoE architecture with fast token decoding and 32k context window",
    },
]


def mask_api_key(key: Optional[str]) -> Optional[str]:
    """Returns safe masked representation: e.g. gsk_...4a9f without exposing raw key."""
    if not key:
        return None
    clean = key.strip()
    if len(clean) <= 8:
        return "gsk_...****"
    return f"{clean[:4]}...{clean[-4:]}"


def save_active_llm_credentials(api_key: str, model: str) -> None:
    """Persists encrypted active Groq credentials in agent_app.sqlite."""
    import sqlite3
    from backend.app.db.security import encrypt_connection_params
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    try:
        enc_payload = encrypt_connection_params({"api_key": api_key})
        with conn:
            conn.execute(
                """
                INSERT INTO active_llm_config (id, provider, model, api_key_enc, status, updated_at)
                VALUES ('active_llm', 'groq', ?, ?, 'CONNECTED', CURRENT_TIMESTAMP)
                ON CONFLICT(id) DO UPDATE SET
                    provider = 'groq',
                    model = excluded.model,
                    api_key_enc = excluded.api_key_enc,
                    status = 'CONNECTED',
                    updated_at = CURRENT_TIMESTAMP;
                """,
                (model, enc_payload),
            )
    finally:
        conn.close()


def load_persisted_llm_credentials() -> Optional[Dict[str, str]]:
    """Loads active Groq credentials from agent_app.sqlite if available."""
    import sqlite3
    from backend.app.db.security import decrypt_connection_params
    if not settings.resolved_app_db_path.exists():
        return None
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.cursor()
        cur.execute("SELECT * FROM active_llm_config WHERE id = 'active_llm';")
        row = cur.fetchone()
        if row and row["status"] == "CONNECTED":
            params = decrypt_connection_params(row["api_key_enc"])
            api_key = params.get("api_key")
            if api_key:
                return {"api_key": api_key, "model": row["model"]}
        return None
    except Exception as e:
        logger.debug(f"Could not load persisted LLM config: {e}")
        return None
    finally:
        conn.close()


def clear_persisted_llm_credentials() -> None:
    """Marks LLM as disconnected in agent_app.sqlite."""
    import sqlite3
    if not settings.resolved_app_db_path.exists():
        return
    conn = sqlite3.connect(str(settings.resolved_app_db_path))
    try:
        with conn:
            conn.execute(
                "UPDATE active_llm_config SET status = 'DISCONNECTED', updated_at = CURRENT_TIMESTAMP WHERE id = 'active_llm';"
            )
    finally:
        conn.close()


_active_groq_provider: Optional[GroqLLMProvider] = None


def get_llm_provider() -> BaseLLMProvider:
    """
    Factory returning the active LLM provider.
    Groq is the single supported provider across production and development.
    In automated test environments (APP_ENV='testing') without a real Groq API key,
    returns deterministic MockLLMProvider to prevent external network calls.
    """
    global _active_groq_provider
    if settings.APP_ENV == "testing" and not settings.is_llm_configured():
        return MockLLMProvider()

    if _active_groq_provider is None:
        if not settings.is_llm_configured():
            persisted = load_persisted_llm_credentials()
            if persisted:
                settings.GROQ_API_KEY = persisted["api_key"]
                settings.GROQ_MODEL = persisted["model"]
        _active_groq_provider = GroqLLMProvider()
    return _active_groq_provider


def set_active_groq_credentials(api_key: str, model: Optional[str] = None) -> GroqLLMProvider:
    """Updates active Groq credentials in memory and persists encrypted config."""
    global _active_groq_provider
    settings.GROQ_API_KEY = api_key
    if model:
        settings.GROQ_MODEL = model
    save_active_llm_credentials(api_key, settings.GROQ_MODEL)
    _active_groq_provider = GroqLLMProvider(api_key=api_key, model=settings.GROQ_MODEL)
    return _active_groq_provider


def disconnect_groq_credentials() -> None:
    """Clears in-memory credentials and marks LLM as disconnected in store."""
    global _active_groq_provider
    settings.GROQ_API_KEY = None
    clear_persisted_llm_credentials()
    _active_groq_provider = None
