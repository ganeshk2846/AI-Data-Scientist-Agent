"""
Comprehensive test suite for Groq LLM integration.
Tests single-provider configuration, error boundaries, rate limiting,
bounded retries, structured JSON outputs, streaming, and mock boundary isolation.
Uses standard asyncio.run for robust test execution without external plugins.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from openai import (
    APIConnectionError,
    APIStatusError,
    APITimeoutError,
    AuthenticationError,
    NotFoundError,
    RateLimitError,
)

from backend.app.core.config import settings
from backend.app.core.errors import ConfigurationError
from backend.app.llm.client import (
    BaseLLMProvider,
    GroqLLMProvider,
    MockLLMProvider,
    get_llm_provider,
)
from backend.app.llm.models import LLMMessage, LLMRequest, LLMResponse


def test_groq_missing_api_key_raises_configuration_error():
    """Verifies that missing GROQ_API_KEY raises ConfigurationError without silent mock fallback."""
    async def _test():
        provider = GroqLLMProvider(api_key=None)
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])
        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "GROQ_API_KEY is not configured" in str(exc_info.value)
        assert not isinstance(exc_info.value, LLMResponse)

    asyncio.run(_test())


def test_groq_placeholder_api_key_raises_configuration_error():
    """Verifies that placeholder GROQ_API_KEY raises ConfigurationError without silent mock fallback."""
    async def _test():
        provider = GroqLLMProvider(api_key="your_groq_api_key_here")
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])
        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "placeholder" in str(exc_info.value).lower() or "not configured" in str(exc_info.value).lower()

    asyncio.run(_test())


def test_groq_authentication_failure_handled():
    """Verifies HTTP 401 AuthenticationError is mapped to ConfigurationError with clear guidance."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_invalid_test_key_12345")
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

        mock_client = MagicMock()
        mock_response = httpx.Response(
            status_code=401,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )
        auth_err = AuthenticationError("Invalid API Key", response=mock_response, body={"error": "invalid_api_key"})
        mock_client.chat.completions.create = AsyncMock(side_effect=auth_err)
        provider._client = mock_client

        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "401" in str(exc_info.value)
        assert "GROQ_API_KEY" in str(exc_info.value)

    asyncio.run(_test())


def test_groq_not_found_model_handled():
    """Verifies HTTP 404 NotFoundError is mapped to ConfigurationError mentioning model."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key", model="non-existent-model-xyz")
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

        mock_client = MagicMock()
        mock_response = httpx.Response(
            status_code=404,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )
        not_found_err = NotFoundError("Model not found", response=mock_response, body={"error": "model_not_found"})
        mock_client.chat.completions.create = AsyncMock(side_effect=not_found_err)
        provider._client = mock_client

        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "404" in str(exc_info.value)
        assert "GROQ_MODEL" in str(exc_info.value)

    asyncio.run(_test())


def test_groq_rate_limit_and_bounded_retry_success():
    """Verifies bounded retry recovers from transient 429 rate limit errors."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key", max_retries=2)
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

        mock_response_obj = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = "Recovered response"
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"
        mock_response_obj.choices = [mock_choice]
        mock_response_obj.usage.total_tokens = 45
        mock_response_obj.usage.prompt_tokens = 15
        mock_response_obj.usage.completion_tokens = 30

        mock_http_res = httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )
        rate_err = RateLimitError("Rate limit reached", response=mock_http_res, body={})

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=[rate_err, mock_response_obj])
        provider._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            res = await provider.generate(req)
            assert res.content == "Recovered response"
            assert res.tokens_used == 45
            assert res.provider == "groq"
            assert mock_sleep.call_count == 1

    asyncio.run(_test())


def test_groq_rate_limit_exhausted_raises_configuration_error():
    """Verifies that exceeding max retries on 429 raises ConfigurationError."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key", max_retries=2)
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

        mock_http_res = httpx.Response(
            status_code=429,
            request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
        )
        rate_err = RateLimitError("Rate limit reached", response=mock_http_res, body={})

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(side_effect=rate_err)
        provider._client = mock_client

        with patch("asyncio.sleep", new_callable=AsyncMock):
            with pytest.raises(ConfigurationError) as exc_info:
                await provider.generate(req)
            assert "rate limit exceeded after 2 retries" in str(exc_info.value).lower()

    asyncio.run(_test())


def test_groq_timeout_handled():
    """Verifies APITimeoutError is mapped to ConfigurationError with timeout duration."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key", timeout_seconds=10)
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")], timeout_seconds=5)

        mock_client = MagicMock()
        timeout_err = APITimeoutError(request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))
        mock_client.chat.completions.create = AsyncMock(side_effect=timeout_err)
        provider._client = mock_client

        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "timed out after 5s" in str(exc_info.value)

    asyncio.run(_test())


def test_groq_connection_error_handled():
    """Verifies APIConnectionError is mapped to ConfigurationError with base URL."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key")
        req = LLMRequest(messages=[LLMMessage(role="user", content="Hello")])

        mock_client = MagicMock()
        conn_err = APIConnectionError(request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"))
        mock_client.chat.completions.create = AsyncMock(side_effect=conn_err)
        provider._client = mock_client

        with pytest.raises(ConfigurationError) as exc_info:
            await provider.generate(req)
        assert "Failed to connect to Groq API" in str(exc_info.value)

    asyncio.run(_test())


def test_groq_structured_json_request():
    """Verifies response_format={'type': 'json_object'} is passed through to Groq API."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key")
        req = LLMRequest(
            messages=[
                LLMMessage(role="system", content="Return JSON object."),
                LLMMessage(role="user", content="Output metrics."),
            ],
            response_format={"type": "json_object"},
        )

        mock_response_obj = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = '{"revenue": 100000.0, "status": "verified"}'
        mock_choice.message.tool_calls = None
        mock_choice.finish_reason = "stop"
        mock_response_obj.choices = [mock_choice]
        mock_response_obj.usage.total_tokens = 60
        mock_response_obj.usage.prompt_tokens = 25
        mock_response_obj.usage.completion_tokens = 35

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_response_obj)
        provider._client = mock_client

        res = await provider.generate(req)
        assert res.content == '{"revenue": 100000.0, "status": "verified"}'
        assert res.prompt_tokens == 25
        assert res.completion_tokens == 35
        assert res.tokens_used == 60

        call_kwargs = mock_client.chat.completions.create.call_args.kwargs
        assert call_kwargs["response_format"] == {"type": "json_object"}
        assert call_kwargs["model"] == settings.GROQ_MODEL

    asyncio.run(_test())


def test_groq_streaming_generator():
    """Verifies stream_generate yields chunks sequentially from Groq stream."""
    async def _test():
        provider = GroqLLMProvider(api_key="gsk_valid_key")
        req = LLMRequest(messages=[LLMMessage(role="user", content="Stream response")])

        async def mock_stream_chunks():
            tokens = ["Executive ", "summary: ", "revenue ", "grew ", "15%."]
            for t in tokens:
                chunk = MagicMock()
                delta = MagicMock()
                delta.content = t
                choice = MagicMock()
                choice.delta = delta
                chunk.choices = [choice]
                yield chunk

        mock_client = MagicMock()
        mock_client.chat.completions.create = AsyncMock(return_value=mock_stream_chunks())
        provider._client = mock_client

        collected = []
        async for chunk in provider.stream_generate(req):
            collected.append(chunk)

        assert "".join(collected) == "Executive summary: revenue grew 15%."

    asyncio.run(_test())


def test_groq_streaming_missing_key_raises_configuration_error():
    """Verifies stream_generate raises ConfigurationError when key is missing."""
    async def _test():
        provider = GroqLLMProvider(api_key=None)
        req = LLMRequest(messages=[LLMMessage(role="user", content="Stream response")])

        with pytest.raises(ConfigurationError) as exc_info:
            async for _ in provider.stream_generate(req):
                pass
        assert "GROQ_API_KEY is not configured" in str(exc_info.value)

    asyncio.run(_test())


def test_get_llm_provider_testing_mode_vs_production_mode():
    """
    Verifies that get_llm_provider():
    - Returns MockLLMProvider in automated testing when no key is set.
    - Returns GroqLLMProvider in production or development mode regardless of key presence.
    """
    orig_env = settings.APP_ENV
    orig_key = settings.GROQ_API_KEY
    try:
        # 1. Testing mode without key -> MockLLMProvider
        settings.APP_ENV = "testing"
        settings.GROQ_API_KEY = None
        p1 = get_llm_provider()
        assert isinstance(p1, MockLLMProvider)

        # 2. Testing mode with key -> GroqLLMProvider
        settings.APP_ENV = "testing"
        settings.GROQ_API_KEY = "gsk_test_valid_key"
        p2 = get_llm_provider()
        assert isinstance(p2, GroqLLMProvider)

        # 3. Production mode without key -> GroqLLMProvider (raises on generate, NEVER mock)
        settings.APP_ENV = "production"
        settings.GROQ_API_KEY = None
        p3 = get_llm_provider()
        assert isinstance(p3, GroqLLMProvider)
    finally:
        settings.APP_ENV = orig_env
        settings.GROQ_API_KEY = orig_key


def test_mock_provider_deterministic_behavior():
    """Verifies that MockLLMProvider behaves deterministically for test isolation."""
    async def _test():
        mock_p = MockLLMProvider()

        # SQL prompt
        sql_req = LLMRequest(
            messages=[
                LLMMessage(role="system", content="Generate sqlite select query"),
                LLMMessage(role="user", content="What are total sales by year?"),
            ]
        )
        sql_res = await mock_p.generate(sql_req)
        assert "select" in sql_res.content.lower()
        assert "orders" in sql_res.content.lower()

        # Router prompt
        router_req = LLMRequest(
            messages=[
                LLMMessage(role="system", content="Classify user query router"),
                LLMMessage(role="user", content="Forecast monthly sales next month"),
            ]
        )
        router_res = await mock_p.generate(router_req)
        assert "predictive" in router_res.content.lower()

    asyncio.run(_test())
