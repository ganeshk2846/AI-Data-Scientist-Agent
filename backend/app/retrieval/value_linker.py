"""
Value Linker for safe, low-cardinality categorical entities.
Maps fuzzy or colloquial user expressions to exact database literal values.
Operates dynamically against the active schema catalog, with e-commerce mappings
strictly gated on verified schema domain compatibility.
"""

import re
from typing import List, Optional
from pydantic import BaseModel, Field
from backend.app.schema.models import DatabaseCatalog


class LinkedValue(BaseModel):
    user_mention: str
    target_table: str
    target_column: str
    exact_db_value: str
    confidence: float = 1.0


# Domain-specific mappings: Gated strictly on e-commerce schema presence
ECOMMERCE_LITERAL_MAPPINGS = [
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

# Backward compatibility alias
KNOWN_LITERAL_MAPPINGS = ECOMMERCE_LITERAL_MAPPINGS


class ValueLinker:
    """Links natural language tokens to database literal values with domain isolation."""

    def link_values(self, query: str, catalog: Optional[DatabaseCatalog] = None) -> List[LinkedValue]:
        query_lower = query.lower()
        linked: List[LinkedValue] = []
        seen_keys = set()

        cat = catalog
        if cat is None:
            try:
                from backend.app.schema.service import schema_service
                cat = schema_service.get_cached_catalog()
            except Exception:
                pass

        # 1. Dynamic Discovery from Active Schema Catalog (Domain-Independent)
        if cat and cat.tables:
            for tbl_name, tbl_model in cat.tables.items():
                for col in tbl_model.columns:
                    # Scan low-cardinality categorical columns
                    if col.sample_values and (col.distinct_count <= 50 or len(col.sample_values) <= 20):
                        for sample in col.sample_values:
                            sample_str = str(sample).strip()
                            if len(sample_str) >= 2:
                                pattern = rf"\b{re.escape(sample_str.lower())}\b"
                                match = re.search(pattern, query_lower)
                                if match:
                                    pair_key = (tbl_name, col.name, sample_str)
                                    if pair_key not in seen_keys:
                                        seen_keys.add(pair_key)
                                        linked.append(
                                            LinkedValue(
                                                user_mention=match.group(0),
                                                target_table=tbl_name,
                                                target_column=col.name,
                                                exact_db_value=sample_str,
                                                confidence=0.95,
                                            )
                                        )

        # 2. Specialized E-commerce Mappings: Only applied if schema has matching tables and columns
        if cat and cat.tables:
            is_ecom = "orders" in cat.tables or "customer_segments" in cat.tables
            if is_ecom:
                for pattern, table, col, exact_val in ECOMMERCE_LITERAL_MAPPINGS:
                    # Verify table and column exist in active catalog
                    if table in cat.tables:
                        col_names = {c.name.lower() for c in cat.tables[table].columns}
                        if col.lower() in col_names:
                            match = re.search(pattern, query_lower)
                            if match:
                                pair_key = (table, col, exact_val)
                                if pair_key not in seen_keys:
                                    seen_keys.add(pair_key)
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
