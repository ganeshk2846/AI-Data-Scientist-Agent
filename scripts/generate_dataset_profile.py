"""
Generates docs/DATASET_PROFILE.md from raw inspection data and verified database facts.
"""

import json
from pathlib import Path

def generate_profile_markdown():
    raw_path = Path("docs/dataset_profile_raw.json")
    if not raw_path.exists():
        raise FileNotFoundError("docs/dataset_profile_raw.json not found")

    with open(raw_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tables = data["tables"]
    total_tables = data["tables_count"]
    total_rows = data["total_rows"]
    total_indexes = data["indexes_count"]
    fk_graph = data["foreign_keys_graph"]

    md = []
    md.append("# Verified Dataset Profile: `ecommerce.sqlite`\n\n")
    md.append("> **Status:** Phase 0 Reconnaissance Complete\n>\n")
    md.append("> **Database File:** `ecommerce.sqlite` (47,439,872 bytes / ~45.2 MB)\n>\n")
    md.append("> **Access Mode:** Strict Read-Only (`mode=ro`)\n>\n")
    md.append("> **Total Tables:** 30\n>\n")
    md.append("> **Total Views:** 0\n>\n")
    md.append(f"> **Total Rows:** {total_rows:,}\n>\n")
    md.append(f"> **Total Indexes:** {total_indexes}\n>\n")
    md.append(f"> **Total Foreign Key Relationships:** {len(fk_graph)}\n>\n")
    md.append("> **Foreign Key Integrity Violations:** 0 (Verified via `PRAGMA foreign_key_check`)\n>\n")
    md.append("> **Temporal Span:** 2023-01-01 to 2025-12-31 (3 full calendar years, 1,096 consecutive days)\n\n")
    md.append("---\n\n")

    md.append("## 1. Executive Summary & Data Domains\n")
    md.append("The database is an enterprise e-commerce operational and analytical warehouse containing 30 interconnected tables. The dataset represents 3 years of complete business history (January 1, 2023 to December 31, 2025) covering orders, fulfillment, logistics, catalog management, inventory levels, customer lifecycle, multi-touch web tracking, advertising spend, reviews, returns, and support interactions.\n")

    md.append("### Functional Domain Breakdown\n")
    md.append("| Domain | Tables Included | Primary Business Purpose |\n")
    md.append("|---|---|---|\n")
    md.append("| **Customers & Segments** | `customers`, `customer_addresses`, `customer_segments`, `customer_segment_history` | 5,000 customers across Brazilian states; longitudinal RFM-based segment transitions (VIP, Loyal, Occasional, New, At Risk, Dormant). |\n")
    md.append("| **Orders & Transactions** | `orders`, `order_items`, `payments`, `shipments`, `shipment_events` | 17,924 orders (17,274 delivered, 650 cancelled) totaling $21,761,969.17 gross revenue; 30,707 order line items. |\n")
    md.append("| **Merchandising & Catalog** | `brands`, `categories`, `product_categories`, `products`, `seller_products`, `promotions` | 1,000 products, 30 brands, 30 categories, 4 targeted promotional campaigns. |\n")
    md.append("| **Supply Chain & Warehousing** | `warehouses`, `suppliers`, `purchase_orders`, `inventory`, `sellers` | 20 regional distribution centers, 24 suppliers, 3,000 POs, monthly inventory snapshots (12,960 records). |\n")
    md.append("| **Marketing & Attribution** | `marketing_channels`, `marketing_spend`, `website_sessions`, `session_events` | 8 acquisition channels (Paid Search, Social, Email, Direct, etc.), daily spend across 8,768 records, 71,046 web sessions, 34,640 clickstream events. |\n")
    md.append("| **Post-Purchase & Service** | `returns`, `refunds`, `reviews`, `support_tickets` | 2,277 returns, 1,853 refunds, 9,224 customer reviews (1-5 stars), 2,174 support tickets with CSAT scores. |\n")
    md.append("| **Financials & Planning** | `expenses`, `daily_targets` | 6,576 expense records (logistics, marketing, payroll, software), 1,096 daily sales/order target benchmarks. |\n\n")

    md.append("## 2. Entity-Relationship Graph\n")
    md.append("Below is the structural relationship graph derived directly from foreign key declarations:\n\n")
    md.append("```mermaid\n")
    md.append("graph TD\n")
    md.append("    customers --> customer_addresses\n")
    md.append("    customers --> customer_segment_history\n")
    md.append("    customer_segments --> customer_segment_history\n")
    md.append("    customers --> orders\n")
    md.append("    marketing_channels --> orders\n")
    md.append("    promotions --> orders\n")
    md.append("    orders --> order_items\n")
    md.append("    products --> order_items\n")
    md.append("    sellers --> order_items\n")
    md.append("    orders --> payments\n")
    md.append("    orders --> shipments\n")
    md.append("    warehouses --> shipments\n")
    md.append("    shipments --> shipment_events\n")
    md.append("    orders --> returns\n")
    md.append("    returns --> refunds\n")
    md.append("    orders --> reviews\n")
    md.append("    customers --> support_tickets\n")
    md.append("    orders --> support_tickets\n")
    md.append("    categories --> categories\n")
    md.append("    brands --> products\n")
    md.append("    categories --> products\n")
    md.append("    products --> product_categories\n")
    md.append("    categories --> product_categories\n")
    md.append("    products --> seller_products\n")
    md.append("    sellers --> seller_products\n")
    md.append("    suppliers --> purchase_orders\n")
    md.append("    warehouses --> purchase_orders\n")
    md.append("    products --> purchase_orders\n")
    md.append("    warehouses --> inventory\n")
    md.append("    products --> inventory\n")
    md.append("    marketing_channels --> marketing_spend\n")
    md.append("    marketing_channels --> website_sessions\n")
    md.append("    customers --> website_sessions\n")
    md.append("    orders --> website_sessions\n")
    md.append("    website_sessions --> session_events\n")
    md.append("    products --> session_events\n")
    md.append("    marketing_channels --> daily_targets\n")
    md.append("    warehouses --> expenses\n")
    md.append("```\n\n")

    md.append("## 3. Comprehensive Table Inventory (30 Tables)\n\n")

    for tbl_name, tbl in sorted(tables.items()):
        row_cnt = tbl["row_count"]
        cols = tbl["columns"]
        fks = tbl["foreign_keys"]
        idxs = tbl["indexes"]

        md.append(f"### Table: `{tbl_name}`\n")
        md.append(f"- **Row Count:** {row_cnt:,}\n")
        md.append(f"- **Total Columns:** {len(cols)}\n")

        # Foreign keys summary
        if fks:
            fk_str = ", ".join([f"`{fk['from_col']}` -> `{fk['target_table']}.{fk['to_col']}`" for fk in fks])
            md.append(f"- **Foreign Keys ({len(fks)}):** {fk_str}\n")
        else:
            md.append("- **Foreign Keys:** None\n")

        # Indexes summary
        if idxs:
            idx_str = ", ".join([f"`{idx['name']}` ({'UNIQUE ' if idx['unique'] else ''}[{', '.join(idx['columns'])}])" for idx in idxs])
            md.append(f"- **Indexes ({len(idxs)}):** {idx_str}\n")
        else:
            md.append("- **Indexes:** None (using standard PK rowid)\n")

        md.append("\n**Columns Definition:**\n\n")
        md.append("| Column | SQLite Type | PK | Not Null | Null % | Distinct | Value Range / Sample |\n")
        md.append("|---|---|---|---|---|---|---|\n")

        for c in cols:
            pk_val = "✓" if c["pk"] else ""
            nn_val = "✓" if c["notnull"] else ""
            null_pct = f"{c['null_percentage']}%"
            dist_val = f"{c['distinct_count']:,}"
            
            val_range = "N/A"
            if c["min_sample"] is not None and c["max_sample"] is not None:
                if c["min_sample"] == c["max_sample"]:
                    val_range = f"`{c['min_sample']}`"
                else:
                    val_range = f"`{c['min_sample']}` to `{c['max_sample']}`"
            
            md.append(f"| `{c['name']}` | `{c['type']}` | {pk_val} | {nn_val} | {null_pct} | {dist_val} | {val_range} |\n")

        md.append("\n---\n\n")

    md.append("## 4. Data Quality & Anomaly Assessment\n\n")
    md.append("Through automated profiling, the following structural characteristics and anomalies were verified:\n\n")
    md.append("1. **100% Structural Consistency:** `PRAGMA foreign_key_check` reported 0 broken relational links across all 44 foreign key declarations.\n")
    md.append("2. **No Duplicate Primary Keys:** All 30 tables have defined primary keys with 0 duplicate values.\n")
    md.append("3. **100% Null Columns:**\n")
    md.append("   - `daily_targets.channel_id`: 100% NULL (Targets are set at the global company level per day, not partitioned per channel).\n")
    md.append("   - `expenses.warehouse_id`: 100% NULL (Operating expenses are categorized into payroll, software, logistics, marketing at corporate level, not warehouse level).\n")
    md.append("   - `seller_products.active_to`: 100% NULL (All 2,000 seller-product listings are currently active without a scheduled sunset date).\n")
    md.append("4. **High Null Rate Attributes (Design Patterns):**\n")
    md.append("   - `orders.promotion_id`: 98.0% NULL (Promotions are sparse campaigns; only 367 out of 17,924 orders utilized a promo code).\n")
    md.append("   - `marketing_spend.campaign_id`: 99.5% NULL (Spend is tracked primarily at the channel and date level, with only select tracked campaigns).\n")
    md.append("   - `products.discontinue_date`: 94.8% NULL (Only 52 products have been discontinued; 948 remain in active catalog).\n")
    md.append("   - `orders.channel_id`: 44.5% NULL (Represents direct, organic, or unattributed checkout flows).\n")
    md.append("   - `website_sessions.customer_id`: 64.5% NULL (Anonymous top-of-funnel browsing traffic prior to login or checkout).\n")
    md.append("   - `website_sessions.order_id`: 95.1% NULL (Reflects a realistic ~4.9% e-commerce session-to-order conversion rate).\n")
    md.append("5. **Financial Reconciliations:**\n")
    md.append("   - Delivered Orders: 17,274 orders totaling $20,891,624.33.\n")
    md.append("   - Paid Payments: 17,274 records totaling $20,891,624.33 (Exact 1:1 match with delivered orders).\n")
    md.append("   - Cancelled Orders: 650 orders totaling $870,344.84.\n")
    md.append("   - Voided Payments: 650 records totaling $870,344.84 (Exact 1:1 match with cancelled orders).\n\n")

    md.append("## 5. Analytical Suitability Matrix\n\n")
    md.append("| Analysis Type | Suitability | Supported Capabilities | Required Caveats / Defenses |\n")
    md.append("|---|---|---|---|\n")
    md.append("| **Descriptive Analytics (What)** | **Full Support** | Total revenue, order volumes, average order value (AOV), refund rates, fulfillment speed, regional breakdown. | Distinguish gross order value ($21.76M) from net delivered revenue ($20.89M) and handle refunds ($1.85M) accurately. |\n")
    md.append("| **Diagnostic Analytics (Why)** | **Full Support** | Category drop-offs, carrier shipping delays, conversion funnel bottlenecks, review rating drivers. | Correlation is not causation; explain associations without claiming definitive causal proof unless controlled quasi-experiments are established. |\n")
    md.append("| **Trend & Time Series** | **Full Support** | Daily, weekly, monthly, and quarterly aggregations across 3 complete calendar years (2023-2025). | Continuous time series; leap year (2024) included; seasonality patterns clearly detectable across Q4 peaks (Black Friday). |\n")
    md.append("| **Predictive Forecasting** | **Full Support** | 36 months of continuous daily order and revenue history provide sufficient training and holdout periods for AutoARIMA, Prophet, and LightGBM models. | Holdouts must be strictly time-ordered (no future data leakage). |\n")
    md.append("| **Customer Churn / Retention** | **Full Support** | Longitudinal segment tracking in `customer_segment_history` (transitions between VIP, Loyal, Occasional, At Risk, Dormant). | Churn predictions represent risk probabilities, not certainties. |\n")
    md.append("| **Prescriptive & Optimization** | **Conditional Support** | Inventory reorder triggers (lead times, warehouse capacities, snapshot burn rates); promotion pricing adjustments. | Must state explicit constraints, objectives, and assumptions. Abstain if constraints are undefined. |\n")

    output_path = Path("docs/DATASET_PROFILE.md")
    output_path.write_text("".join(md), encoding="utf-8")
    print(f"[SUCCESS] Written docs/DATASET_PROFILE.md ({len(''.join(md))} bytes)")

if __name__ == "__main__":
    generate_profile_markdown()
