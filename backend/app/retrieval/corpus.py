"""
Schema Corpus Builder.
Constructs rich searchable text documents for each table, column, and business relation.
"""

import re
from typing import Dict, List
from pydantic import BaseModel, Field
from backend.app.schema.models import DatabaseCatalog, TableModel

DOMAIN_DESCRIPTIONS = {
    "customers": "Customer master directory, profiles, buyer demographic details, signup date, state, and active status.",
    "customer_addresses": "Customer shipping and billing addresses, street, city, state, zip code.",
    "customer_segments": "RFM customer lifecycle segments: VIP, Loyal, Occasional, New, At Risk, Dormant.",
    "customer_segment_history": "Longitudinal record of customer transitions between RFM segments over time, valid from and to dates.",
    "orders": "Master sales orders, customer purchases, order status (delivered, cancelled), total amount, payment channels, promotion links.",
    "order_items": "Individual product line items within orders, quantity, unit price, subtotal, seller references.",
    "payments": "Financial payment transactions, payment methods (credit card, debit, voucher, boleto), payment status (paid, voided), and amount.",
    "shipments": "Order fulfillment, package shipping tracking, delivery carriers, estimated delivery, and delivered timestamps.",
    "shipment_events": "Logistics tracking milestones, shipping carrier events, package status scans, delivery updates.",
    "brands": "Merchandise brand manufacturers and catalog brand labels.",
    "categories": "Product category hierarchy, parent and child department taxonomies.",
    "product_categories": "Product to category association mapping table.",
    "products": "Product catalog items, SKU names, retail price, cost, product launch date, dimensions, weight.",
    "seller_products": "Marketplace seller product inventory offerings and active pricing.",
    "promotions": "Discount campaigns, promotional discount rates, coupon codes (Black Friday, Fashion Week, Sports Week, Home Refresh).",
    "warehouses": "Fulfillment distribution centers, warehouse locations, cities, states, storage capacity.",
    "suppliers": "Supply chain vendors, manufacturing suppliers, supplier lead times, and states.",
    "purchase_orders": "Inventory replenishment purchase orders, wholesale buying from suppliers to warehouses.",
    "inventory": "Warehouse stock levels, monthly snapshot dates, available quantity on hand, inventory valuation.",
    "sellers": "Marketplace third-party sellers, vendor accounts, seller states.",
    "marketing_channels": "Customer acquisition channels: Paid Search, Paid Social, Email, Direct, Referral, Display.",
    "marketing_spend": "Daily marketing advertising spend, channel marketing budgets, campaign costs, clicks, impressions.",
    "website_sessions": "Web traffic sessions, browser visits, attribution marketing channels, customer session tracking.",
    "session_events": "Web clickstream actions, pageviews, cart adds, search events, product views.",
    "returns": "Product returns, customer return requests, return reasons, approved and rejected returns.",
    "refunds": "Financial refunds, returned payment reimbursement, processed refund amounts.",
    "reviews": "Customer feedback, product reviews, rating stars (1 to 5), review comments, customer satisfaction.",
    "support_tickets": "Customer care service tickets, complaints, support issues, resolution times, satisfaction score (CSAT).",
    "expenses": "Operational corporate expenditures, logistics expenses, marketing costs, software and payroll overhead.",
    "daily_targets": "Daily business targets, benchmark sales goals, revenue target expectations, order volume quotas.",
}


class TableDocument(BaseModel):
    table_name: str
    domain: str
    row_count: int
    column_names: List[str]
    column_descriptions: List[str]
    foreign_keys: List[str]
    sample_values: List[str]
    search_text: str
    tokens: List[str]


def tokenize_text(text: str) -> List[str]:
    """Splits text on non-alphanumeric chars, lowercases, and removes short tokens."""
    tokens = re.findall(r"\b[a-zA-Z0-9_]{2,}\b", text.lower())
    # Expand snake_case tokens
    expanded = []
    for tok in tokens:
        expanded.append(tok)
        if "_" in tok:
            for part in tok.split("_"):
                if len(part) >= 2:
                    expanded.append(part)
    return expanded


class SchemaCorpus:
    """Builds and indexes searchable schema documents."""

    def __init__(self, catalog: DatabaseCatalog):
        self.catalog = catalog
        self.documents: Dict[str, TableDocument] = {}
        self._build_corpus()

    def _build_corpus(self):
        for name, tbl in self.catalog.tables.items():
            domain_desc = DOMAIN_DESCRIPTIONS.get(name, "General Operational Data")
            col_names = [c.name for c in tbl.columns]

            col_descs = []
            safe_samples = []
            for c in tbl.columns:
                role = []
                if c.is_pk:
                    role.append("primary key")
                if c.is_fk:
                    role.append(f"foreign key referencing {c.fk_target_table}.{c.fk_target_column}")
                if c.is_date_candidate:
                    role.append("date timestamp calendar")
                if c.is_numeric_candidate:
                    role.append("numeric metric amount money")
                col_descs.append(f"{c.name} ({c.sqlite_type}): {' '.join(role)}")
                if c.sample_values:
                    safe_samples.extend(c.sample_values)

            fk_links = [f"{fk.source_column} references {fk.target_table}.{fk.target_column}" for fk in tbl.foreign_keys]

            # Composite rich search text
            text_parts = [
                f"Table name: {name}",
                f"Description and business purpose: {domain_desc}",
                f"Columns: {' '.join(col_names)}",
                f"Column details: {' | '.join(col_descs)}",
                f"Foreign key links: {' | '.join(fk_links)}",
                f"Sample categorical values: {' '.join(safe_samples)}",
            ]
            full_text = "\n".join(text_parts)
            tokens = tokenize_text(full_text)

            self.documents[name] = TableDocument(
                table_name=name,
                domain=domain_desc,
                row_count=tbl.row_count,
                column_names=col_names,
                column_descriptions=col_descs,
                foreign_keys=fk_links,
                sample_values=safe_samples,
                search_text=full_text,
                tokens=tokens,
            )
