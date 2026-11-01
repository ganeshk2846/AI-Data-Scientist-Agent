"""
Schema Grounder & Table Retriever.
Identifies relevant tables and foreign key join paths for a given natural language query.
"""

import re
from typing import Dict, List, Set
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service

SYNONYM_TABLE_MAP: Dict[str, List[str]] = {
    "revenue": ["orders", "order_items", "payments"],
    "sales": ["orders", "order_items"],
    "order": ["orders", "order_items"],
    "payment": ["payments", "orders"],
    "paid": ["payments", "orders"],
    "customer": ["customers", "customer_segments", "customer_addresses"],
    "user": ["customers"],
    "segment": ["customer_segments", "customer_segment_history", "customers"],
    "vip": ["customer_segments", "customers"],
    "loyal": ["customer_segments", "customers"],
    "at risk": ["customer_segments", "customer_segment_history", "customers"],
    "product": ["products", "categories", "brands"],
    "item": ["order_items", "products"],
    "category": ["categories", "product_categories", "products"],
    "brand": ["brands", "products"],
    "promotion": ["promotions", "orders"],
    "discount": ["promotions", "orders"],
    "warehouse": ["warehouses", "inventory", "shipments"],
    "inventory": ["inventory", "warehouses", "products"],
    "stock": ["inventory", "warehouses"],
    "supplier": ["suppliers", "purchase_orders"],
    "purchase order": ["purchase_orders", "suppliers", "warehouses"],
    "shipping": ["shipments", "shipment_events", "warehouses"],
    "delivery": ["shipments", "orders"],
    "marketing": ["marketing_channels", "marketing_spend"],
    "channel": ["marketing_channels", "marketing_spend", "orders"],
    "spend": ["marketing_spend", "marketing_channels"],
    "session": ["website_sessions", "session_events"],
    "traffic": ["website_sessions", "marketing_channels"],
    "return": ["returns", "orders", "refunds"],
    "refund": ["refunds", "returns", "orders"],
    "review": ["reviews", "orders", "products"],
    "rating": ["reviews", "products"],
    "ticket": ["support_tickets", "customers"],
    "support": ["support_tickets", "customers"],
    "expense": ["expenses", "warehouses"],
    "cost": ["expenses", "order_items", "products"],
    "target": ["daily_targets", "marketing_channels"],
}


class SchemaGrounder:
    """Retrieves relevant schema elements grounded in verified catalog."""

    def __init__(self):
        pass

    def retrieve_tables(self, query: str, catalog: DatabaseCatalog, max_tables: int = 6) -> List[str]:
        query_lower = query.lower()
        selected: Set[str] = set()

        # 1. Direct table name mentions
        for table_name in catalog.tables.keys():
            pattern = r"\b" + re.escape(table_name) + r"\b"
            if re.search(pattern, query_lower):
                selected.add(table_name)

        # 2. Domain synonym matching
        for keyword, matched_tables in SYNONYM_TABLE_MAP.items():
            if keyword in query_lower:
                for t in matched_tables:
                    if t in catalog.tables:
                        selected.add(t)

        # If nothing matched, default to core business table: orders
        if not selected:
            selected.add("orders")

        # 3. Graph expansion via Foreign Keys:
        # If order_items is selected and products is referenced, or customers and segments
        expanded: Set[str] = set(selected)
        for t in selected:
            tbl_model = catalog.tables.get(t)
            if tbl_model:
                for fk in tbl_model.foreign_keys:
                    if fk.target_table in catalog.tables and len(expanded) < max_tables:
                        # If query mentions a related concept
                        if fk.target_table.lower() in query_lower or fk.source_column.lower() in query_lower:
                            expanded.add(fk.target_table)

        # Return sorted list capped at max_tables
        result = sorted(list(expanded))[:max_tables]
        return result

    def get_grounded_schema_prompt(self, query: str) -> str:
        catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
        relevant_tables = self.retrieve_tables(query, catalog)
        return catalog.to_minimal_prompt_schema(relevant_tables)


schema_grounder = SchemaGrounder()
