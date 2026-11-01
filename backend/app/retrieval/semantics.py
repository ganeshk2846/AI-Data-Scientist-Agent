"""
Semantic Business Definitions and Metric Semantic Layer.
Provides verified business definitions and SQL calculation formulas.
"""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class BusinessMetric(BaseModel):
    name: str
    display_name: str
    formula: str
    description: str
    target_tables: List[str]
    is_verified: bool = True
    synonyms: List[str] = Field(default_factory=list)


CANONICAL_METRICS: Dict[str, BusinessMetric] = {
    "gross_revenue": BusinessMetric(
        name="gross_revenue",
        display_name="Gross Revenue",
        formula="ROUND(SUM(total_amount), 2)",
        description="Total monetary value of all placed orders including cancelled orders.",
        target_tables=["orders"],
        synonyms=["gross sales", "total bookings", "headline revenue"],
    ),
    "net_revenue": BusinessMetric(
        name="net_revenue",
        display_name="Net Delivered Revenue",
        formula="ROUND(SUM(total_amount), 2) WHERE order_status = 'delivered'",
        description="Total monetary value of successfully delivered orders.",
        target_tables=["orders"],
        synonyms=["delivered revenue", "net sales", "realized revenue"],
    ),
    "average_order_value": BusinessMetric(
        name="average_order_value",
        display_name="Average Order Value (AOV)",
        formula="ROUND(AVG(total_amount), 2) WHERE order_status = 'delivered'",
        description="Average ticket size per delivered transaction.",
        target_tables=["orders"],
        synonyms=["aov", "average basket size", "avg ticket"],
    ),
    "return_rate": BusinessMetric(
        name="return_rate",
        display_name="Return Rate",
        formula="ROUND(COUNT(returns.return_id) * 100.0 / COUNT(orders.order_id), 2)",
        description="Percentage of delivered orders that resulted in a customer return.",
        target_tables=["orders", "returns"],
        synonyms=["returns percentage", "order return rate"],
    ),
    "customer_csat": BusinessMetric(
        name="customer_csat",
        display_name="Customer Satisfaction Score (CSAT)",
        formula="ROUND(AVG(satisfaction_score), 2)",
        description="Average CSAT score on resolved support tickets (scale 1 to 5).",
        target_tables=["support_tickets"],
        synonyms=["csat", "satisfaction rating"],
    ),
    "marketing_roas": BusinessMetric(
        name="marketing_roas",
        display_name="Return on Ad Spend (ROAS)",
        formula="revenue / SUM(marketing_spend.spend_amount)",
        description="Revenue generated per dollar of marketing advertising spend.",
        target_tables=["orders", "marketing_spend", "marketing_channels"],
        synonyms=["roas", "marketing efficiency ratio"],
    ),
}


class SemanticRegistry:
    """Manages verified business metrics and synonym mappings."""

    def get_metric(self, name: str) -> Optional[BusinessMetric]:
        return CANONICAL_METRICS.get(name.lower())

    def list_metrics(self) -> List[BusinessMetric]:
        return list(CANONICAL_METRICS.values())

    def find_relevant_metrics(self, query: str) -> List[BusinessMetric]:
        q_lower = query.lower()
        matched = []
        for m in CANONICAL_METRICS.values():
            if m.name in q_lower or m.display_name.lower() in q_lower or any(s in q_lower for s in m.synonyms):
                matched.append(m)
        return matched


semantic_registry = SemanticRegistry()
