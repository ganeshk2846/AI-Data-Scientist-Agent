"""
Answerability Gate and Clarification Policy Agent.
Enforces honest refusal when questions exceed warehouse capabilities,
and asks targeted clarification when queries have ambiguous interpretations.
"""

import re
from typing import List, Optional
from backend.app.agents.contracts import (
    AbstentionType,
    AnswerabilityAssessment,
    ClarificationOption,
    ClarificationResponse,
)
from backend.app.agents.router import RouteResult
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service

UNSUPPORTED_DOMAINS = [
    "stock price", "nasdaq", "crypto", "bitcoin", "ethereum",
    "employee salary", "ceo", "human resources", "hiring",
    "competitor", "amazon price", "walmart",
    "weather", "forecast temperature",
    "password", "secret key", "credit card number",
]


class AnswerabilityGate:
    """Evaluates whether the business question can be faithfully answered by the dataset."""

    def evaluate(self, query: str, route: RouteResult, catalog: DatabaseCatalog) -> AnswerabilityAssessment:
        q_lower = query.lower()

        # Check for completely unsupported domains
        for forbidden in UNSUPPORTED_DOMAINS:
            if forbidden in q_lower:
                return AnswerabilityAssessment(
                    is_answerable=False,
                    confidence=0.99,
                    abstention_type=AbstentionType.UNSUPPORTED_DOMAIN,
                    refusal_reason=(
                        f"The warehouse does not track '{forbidden}'. "
                        "The connected database covers e-commerce operations: orders, customers, products, inventory, marketing, and logistics."
                    ),
                    available_alternatives=[
                        "Orders and gross/net revenue breakdown",
                        "Customer segments and lifetime value",
                        "Product catalog sales and inventory snapshots",
                        "Marketing channels and advertising spend",
                    ],
                )

        # Check for temporal scope (2023 to 2025)
        # If user explicitly asks for 2018 or 2030:
        year_matches = re.findall(r"\b(20[0-9]{2})\b", query)
        for y in year_matches:
            val = int(y)
            if val < 2023 or val > 2025:
                return AnswerabilityAssessment(
                    is_answerable=False,
                    confidence=0.95,
                    abstention_type=AbstentionType.OUT_OF_TEMPORAL_SCOPE,
                    refusal_reason=(
                        f"Data for year {val} is outside the warehouse's temporal boundary. "
                        "The dataset covers January 1, 2023 through December 31, 2025 (3 full calendar years)."
                    ),
                    available_alternatives=[
                        f"Analyze year 2023, 2024, or 2025 performance",
                        "View full 3-year multi-year trend (2023-2025)",
                    ],
                )

        return AnswerabilityAssessment(
            is_answerable=True,
            confidence=0.95,
        )


class ClarificationAgent:
    """Identifies ambiguous queries and formulates targeted clarification options."""

    def check_ambiguity(self, query: str, route: RouteResult) -> ClarificationResponse:
        q_lower = query.lower().strip()

        # Bare comparison query without dimensions
        if q_lower in ["compare revenue", "compare sales", "comparison"]:
            return ClarificationResponse(
                needs_clarification=True,
                question="How would you like to compare revenue?",
                ambiguity_reason="Revenue can be compared across time periods, product categories, customer segments, or marketing channels.",
                default_interpretation="Year-over-Year comparison (2024 vs 2023)",
                options=[
                    ClarificationOption(
                        option_id="opt_yoy",
                        label="Year-over-Year (2023 vs 2024)",
                        description="Compare annual gross revenue between 2023 and 2024",
                        inferred_query="Compare annual revenue between 2023 and 2024",
                    ),
                    ClarificationOption(
                        option_id="opt_cat",
                        label="By Product Category",
                        description="Compare total sales across top product categories",
                        inferred_query="Compare revenue across product categories",
                    ),
                    ClarificationOption(
                        option_id="opt_seg",
                        label="By Customer Segment",
                        description="Compare average spend across VIP, Loyal, and Occasional tiers",
                        inferred_query="Compare revenue across customer segments",
                    ),
                    ClarificationOption(
                        option_id="opt_chan",
                        label="By Marketing Channel",
                        description="Compare revenue generated by marketing acquisition channel",
                        inferred_query="Compare revenue by marketing channel",
                    ),
                ],
            )

        # Bare top customers query without metric
        if q_lower in ["top customers", "best customers"]:
            return ClarificationResponse(
                needs_clarification=True,
                question="Which ranking metric would you like to use for top customers?",
                ambiguity_reason="Customers can be ranked by total lifetime spend (monetary value) or order count (frequency).",
                default_interpretation="Rank by total lifetime spend",
                options=[
                    ClarificationOption(
                        option_id="opt_spend",
                        label="Highest Total Spend ($)",
                        description="Rank customers by total gross order value",
                        inferred_query="Show top 10 customers by total spend",
                    ),
                    ClarificationOption(
                        option_id="opt_orders",
                        label="Most Frequent Orders",
                        description="Rank customers by total order count",
                        inferred_query="Show top 10 customers by order frequency",
                    ),
                ],
            )

        return ClarificationResponse(needs_clarification=False)


answerability_gate = AnswerabilityGate()
clarification_agent = ClarificationAgent()
