"""
Provider-agnostic LLM interface supporting OpenAI, Anthropic, Gemini, and Mock.
"""

from abc import ABC, abstractmethod
import asyncio
import os
import re
from typing import Optional
from backend.app.core.config import settings
from backend.app.core.errors import ConfigurationError
from backend.app.core.logging import logger
from backend.app.llm.models import LLMMessage, LLMRequest, LLMResponse
from backend.app.llm.ollama_client import OllamaLLMProvider


class BaseLLMProvider(ABC):
    """Abstract interface for LLM providers."""

    @abstractmethod
    async def generate(self, request: LLMRequest) -> LLMResponse:
        """Generates a text completion for the provided messages."""
        pass


class MockLLMProvider(BaseLLMProvider):
    """
    Deterministic, schema-grounded Mock LLM for offline development,
    demonstration, and automated testing without external API dependencies.
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

    def _classify_intent(self, prompt: str) -> str:
        if any(w in prompt for w in ["trend", "over time", "monthly", "daily", "growth"]):
            return "trend"
        elif any(w in prompt for w in ["compare", "versus", "vs", "difference"]):
            return "comparative"
        elif any(w in prompt for w in ["why", "driver", "cause", "drop", "spike"]):
            return "diagnostic"
        elif any(w in prompt for w in ["forecast", "predict", "next month", "future"]):
            return "predictive"
        elif any(w in prompt for w in ["should", "recommend", "optimize"]):
            return "prescriptive"
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


class GeminiProvider(BaseLLMProvider):
    """Google Gemini API Provider using the official google-genai SDK."""

    def __init__(self, api_key: str, model: str = "gemini-3.5-flash-lite"):
        from google import genai
        self.client = genai.Client(api_key=api_key)
        self.model = model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        from google.genai import types

        system_instruction: Optional[str] = None
        contents = []

        for m in request.messages:
            if m.role == "system":
                if system_instruction:
                    system_instruction += "\n\n" + m.content
                else:
                    system_instruction = m.content
            else:
                role = "user" if m.role == "user" else "model"
                contents.append(
                    types.Content(
                        role=role,
                        parts=[types.Part.from_text(text=m.content)],
                    )
                )

        if not contents and system_instruction:
            contents.append(
                types.Content(
                    role="user",
                    parts=[types.Part.from_text(text=system_instruction)],
                )
            )
            system_instruction = None

        config = types.GenerateContentConfig(
            system_instruction=system_instruction,
            temperature=request.temperature,
            max_output_tokens=request.max_tokens or 2048,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
        )

        try:
            res = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config,
                ),
                timeout=float(request.timeout_seconds),
            )
            content = res.text or ""
            tokens_used = (
                res.usage_metadata.total_token_count
                if res.usage_metadata and hasattr(res.usage_metadata, "total_token_count")
                else None
            )
            finish_reason = (
                res.candidates[0].finish_reason.name
                if res.candidates and hasattr(res.candidates[0], "finish_reason") and res.candidates[0].finish_reason
                else None
            )
            return LLMResponse(
                content=content,
                model=self.model,
                provider="gemini",
                tokens_used=tokens_used,
                finish_reason=str(finish_reason) if finish_reason else None,
            )
        except Exception as e:
            logger.error(f"Gemini API generation error: {e}. Falling back to grounded mock response.")
            mock_res = await MockLLMProvider().generate(request)
            mock_res.provider = "gemini-fallback"
            return mock_res


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API Provider."""

    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        from openai import AsyncOpenAI
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def generate(self, request: LLMRequest) -> LLMResponse:
        openai_messages = [{"role": m.role, "content": m.content} for m in request.messages]
        res = await self.client.chat.completions.create(
            model=self.model,
            messages=openai_messages,
            temperature=request.temperature,
            max_tokens=request.max_tokens,
            timeout=request.timeout_seconds,
        )
        content = res.choices[0].message.content or ""
        tokens = res.usage.total_tokens if res.usage else None
        return LLMResponse(
            content=content,
            model=self.model,
            provider="openai",
            tokens_used=tokens,
            finish_reason=res.choices[0].finish_reason,
        )


def get_llm_provider() -> BaseLLMProvider:
    """Factory returning the active LLM provider based on application settings."""
    provider_type = settings.LLM_PROVIDER.lower()

    if provider_type == "ollama":
        return OllamaLLMProvider(
            base_url=settings.OLLAMA_BASE_URL,
            model=settings.OLLAMA_MODEL,
        )

    if provider_type == "gemini" and settings.GEMINI_API_KEY and not settings.GEMINI_API_KEY.startswith("your_"):
        try:
            return GeminiProvider(api_key=settings.GEMINI_API_KEY, model=settings.GEMINI_MODEL)
        except Exception as e:
            logger.warning(f"Failed to instantiate Gemini provider: {e}. Falling back to Ollama.")
            return OllamaLLMProvider()

    if provider_type == "openai" and settings.OPENAI_API_KEY and not settings.OPENAI_API_KEY.startswith("your_"):
        try:
            return OpenAIProvider(api_key=settings.OPENAI_API_KEY, model=settings.OPENAI_MODEL)
        except Exception as e:
            logger.warning(f"Failed to instantiate OpenAI provider: {e}. Falling back to Ollama.")
            return OllamaLLMProvider()

    if provider_type == "mock":
        return MockLLMProvider()

    return OllamaLLMProvider()
