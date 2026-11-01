"""
Value Linker for safe, low-cardinality categorical entities.
Maps fuzzy or colloquial user expressions to exact database literal values.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field


class LinkedValue(BaseModel):
    user_mention: str
    target_table: str
    target_column: str
    exact_db_value: str
    confidence: float = 1.0


KNOWN_LITERAL_MAPPINGS = [
    # Customer segments
    (r"\bvip\b", "customer_segments", "segment_name", "VIP"),
    (r"\bloyal\b", "customer_segments", "segment_name", "Loyal"),
    (r"\boccasional\b", "customer_segments", "segment_name", "Occasional"),
    (r"\bat risk\b", "customer_segments", "segment_name", "At Risk"),
    (r"\bdormant\b", "customer_segments", "segment_name", "Dormant"),
    # Order statuses
    (r"\bdelivered\b", "orders", "order_status", "delivered"),
    (r"\bcancelled|canceled\b", "orders", "order_status", "cancelled"),
    # Payment statuses
    (r"\bpaid\b", "payments", "payment_status", "paid"),
    (r"\bvoided|void\b", "payments", "payment_status", "voided"),
    # Payment methods
    (r"\bcredit card|card\b", "payments", "payment_method", "credit_card"),
    (r"\bdebit card\b", "payments", "payment_method", "debit_card"),
    (r"\bboleto\b", "payments", "payment_method", "boleto"),
    (r"\bvoucher\b", "payments", "payment_method", "voucher"),
    # Promotions
    (r"\bblack friday\b", "promotions", "promotion_name", "Black Friday 2024"),
    (r"\bfashion week\b", "promotions", "promotion_name", "Fashion Week 2023"),
    (r"\bsports week\b", "promotions", "promotion_name", "Sports Week 2024"),
    (r"\bhome refresh\b", "promotions", "promotion_name", "Home Refresh 2025"),
    # Marketing channels
    (r"\bpaid search\b", "marketing_channels", "channel_name", "Paid Search"),
    (r"\bpaid social\b", "marketing_channels", "channel_name", "Paid Social"),
    (r"\bemail\b", "marketing_channels", "channel_name", "Email"),
    (r"\borganic search\b", "marketing_channels", "channel_name", "Organic Search"),
    (r"\bdirect\b", "marketing_channels", "channel_name", "Direct"),
]


class ValueLinker:
    """Links natural language tokens to database literal values."""

    def link_values(self, query: str) -> List[LinkedValue]:
        query_lower = query.lower()
        linked: List[LinkedValue] = []

        for pattern, table, col, exact_val in KNOWN_LITERAL_MAPPINGS:
            match = re.search(pattern, query_lower)
            if match:
                linked.append(
                    LinkedValue(
                        user_mention=match.group(0),
                        target_table=table,
                        target_column=col,
                        exact_db_value=exact_val,
                        confidence=0.98,
                    )
                )

        return linked


value_linker = ValueLinker()
