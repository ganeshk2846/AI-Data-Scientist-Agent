"""
Router Agent.
Classifies user intent, question difficulty, and relevant domain entities.
"""

import json
import re
from typing import Any, List, Literal, Optional
from pydantic import BaseModel, Field, field_validator
from backend.app.core.logging import logger
from backend.app.llm.client import BaseLLMProvider, get_llm_provider
from backend.app.llm.models import LLMMessage, LLMRequest

IntentType = Literal[
    "descriptive",
    "comparative",
    "trend",
    "diagnostic",
    "predictive",
    "prescriptive",
]


class RouteResult(BaseModel):
    """Structured routing classification."""
    intent: IntentType
    confidence: float = Field(ge=0.0, le=1.0)
    complexity: Literal["simple", "medium", "complex"] = "simple"
    reasoning: str
    target_domains: List[str] = Field(default_factory=list)
    suggested_entities: List[str] = Field(default_factory=list)

    @field_validator("intent", mode="before")
    @classmethod
    def normalize_intent(cls, v: Any) -> str:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            intent_map = {
                "prediction": "predictive",
                "forecast": "predictive",
                "predictive": "predictive",
                "comparison": "comparative",
                "compare": "comparative",
                "comparative": "comparative",
                "trends": "trend",
                "trending": "trend",
                "trend": "trend",
                "diagnosis": "diagnostic",
                "cause": "diagnostic",
                "diagnostic": "diagnostic",
                "recommendation": "prescriptive",
                "prescription": "prescriptive",
                "prescriptive": "prescriptive",
                "description": "descriptive",
                "descriptive": "descriptive",
            }
            if v_lower in intent_map:
                return intent_map[v_lower]
        return v

    @field_validator("complexity", mode="before")
    @classmethod
    def normalize_complexity(cls, v: Any) -> str:
        if isinstance(v, str):
            v_lower = v.strip().lower()
            if v_lower in ["moderate", "medium", "intermediate", "average", "med"]:
                return "medium"
            if v_lower in ["hard", "difficult", "advanced", "complex", "high"]:
                return "complex"
            if v_lower in ["easy", "basic", "low", "simple"]:
                return "simple"
        return "simple"


ROUTER_SYSTEM_PROMPT = """You are an expert Query Router for an enterprise Business Intelligence Data Scientist Agent.
Classify the user's natural language question into one of the following 6 intent levels:
1. 'descriptive': Facts, totals, averages, order counts, status breakdowns ("What is our total revenue?").
2. 'comparative': Segment or period contrasts ("Compare VIP vs Loyal average order value").
3. 'trend': Trajectory or seasonality over time ("Monthly sales trend in 2024").
4. 'diagnostic': Explanations, drivers, correlation, drop-offs ("Why did orders drop in region SP?").
5. 'predictive': Estimating future behavior, risk, or forecasts ("Which customer segments are likely to churn?").
6. 'prescriptive': Recommendations, optimization ("What price discount should we set?").

Respond ONLY with valid JSON in this exact structure:
{
  "intent": "descriptive",
  "confidence": 0.95,
  "complexity": "simple",
  "reasoning": "Brief explanation",
  "target_domains": ["Orders & Transactions"],
  "suggested_entities": ["orders", "total_amount"]
}
"""


class RouterAgent:
    """Classifies user queries to determine execution workflow."""

    def __init__(self, llm_provider: Optional[BaseLLMProvider] = None):
        self.llm = llm_provider or get_llm_provider()

    async def route(self, query: str) -> RouteResult:
        query_clean = query.strip()
        lower = query_clean.lower()

        # Deterministic heuristic fast-path
        if any(w in lower for w in ["forecast", "predict", "churn", "likelihood"]):
            return RouteResult(
                intent="predictive",
                confidence=0.92,
                complexity="complex",
                reasoning="Query asks for forecasting or future probability.",
                target_domains=["Customers & Segments", "Orders & Transactions"],
                suggested_entities=["customer_segment_history", "orders"],
            )
        elif any(w in lower for w in ["why", "driver", "cause", "drop sharply", "spike"]):
            return RouteResult(
                intent="diagnostic",
                confidence=0.88,
                complexity="complex",
                reasoning="Query asks for causal or contributing factors behind an outcome.",
                target_domains=["Orders & Transactions", "Shipments", "Marketing & Attribution"],
                suggested_entities=["orders", "shipments", "marketing_spend"],
            )
        elif any(w in lower for w in ["trend", "over time", "monthly", "weekly", "by year", "growth"]):
            return RouteResult(
                intent="trend",
                confidence=0.95,
                complexity="medium",
                reasoning="Query asks for time-series trajectory over dates.",
                target_domains=["Orders & Transactions"],
                suggested_entities=["orders", "order_date", "total_amount"],
            )
        elif any(w in lower for w in ["compare", "versus", "vs", "difference between"]):
            return RouteResult(
                intent="comparative",
                confidence=0.90,
                complexity="medium",
                reasoning="Query compares two or more entities or groups.",
                target_domains=["Customers & Segments", "Merchandising & Catalog"],
                suggested_entities=["customers", "customer_segments", "categories"],
            )
        elif any(w in lower for w in ["what if", "scenario", "simulate", "elasticity", "price increase", "price decrease"]):
            return RouteResult(
                intent="predictive",
                confidence=0.90,
                complexity="complex",
                reasoning="Query asks for what-if scenario simulation or sensitivity analysis.",
                target_domains=["Financials & Planning", "Merchandising & Catalog"],
                suggested_entities=["orders", "products"],
            )
        elif any(w in lower for w in ["should we", "recommend", "optimize", "action to take"]):
            return RouteResult(
                intent="prescriptive",
                confidence=0.85,
                complexity="complex",
                reasoning="Query asks for prescriptive action or recommendation.",
                target_domains=["Financials & Planning", "Inventory"],
                suggested_entities=["expenses", "inventory", "daily_targets"],
            )
        elif any(lower.startswith(prefix) for prefix in [
            "what are", "what is", "how many", "show", "list", "display", "count",
            "which tables", "who are", "find", "get", "total"
        ]) or any(w in lower for w in ["total orders", "total sales", "total revenue", "order count", "customer count", "tables in database", "schema"]):
            return RouteResult(
                intent="descriptive",
                confidence=0.96,
                complexity="simple",
                reasoning="Deterministic fast-path: fact retrieval, aggregation, or schema lookup.",
                target_domains=["Orders & Transactions"],
                suggested_entities=["orders"],
            )

        # Default descriptive LLM routing
        try:
            req = LLMRequest(
                messages=[
                    LLMMessage(role="system", content=ROUTER_SYSTEM_PROMPT),
                    LLMMessage(role="user", content=query_clean),
                ],
                temperature=0.0,
                timeout_seconds=8,
            )
            res = await self.llm.generate(req)
            # Parse JSON
            match = re.search(r"\{.*\}", res.content, re.DOTALL)
            if match:
                parsed = json.loads(match.group(0))
                return RouteResult.model_validate(parsed)
        except Exception as e:
            logger.warning(f"LLM routing failed, falling back to descriptive: {e}")

        return RouteResult(
            intent="descriptive",
            confidence=0.95,
            complexity="simple",
            reasoning="Default classification: fact retrieval or aggregation query.",
            target_domains=["Orders & Transactions"],
            suggested_entities=["orders"],
        )


router_agent = RouterAgent()

