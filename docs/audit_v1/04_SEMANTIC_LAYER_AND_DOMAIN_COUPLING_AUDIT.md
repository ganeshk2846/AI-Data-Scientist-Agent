# 04 — Semantic Layer and Domain Coupling Audit

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Principal Software Architect, Text-to-SQL Specialist, Data Governance Auditor  
**Scope:** Exhaustive search and inventory of all hardcoded domain assumptions, fixed formulas, static date ranges, pre-baked table/column references, and semantic layer implementations.

---

## 1. Semantic Layer Audit

### 1.1 Existing Semantic Layer Implementation
The application does **not** have a formal, dynamic semantic layer (such as Cube.js, dbt Semantic Layer, or a dynamic metric store).
Instead, business semantics are represented as a static Python dictionary in [`backend/app/retrieval/semantics.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py):
- **Model:** [`BusinessMetric`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L10-L18)
  - `name: str`
  - `display_name: str`
  - `formula: str`
  - `description: str`
  - `target_tables: List[str]`
  - `is_verified: bool = True`
  - `synonyms: List[str]`
- **Registry:** [`SemanticRegistry`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L72-L88) exposes `get_metric()`, `list_metrics()`, and `find_relevant_metrics()`.

### 1.2 Canonical Metric Definitions Inventory
All 6 metrics defined in [`CANONICAL_METRICS`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L20-L69) assume a specific e-commerce schema:

| Metric Name | Display Name | Static Formula | Assumed Tables | Assumed Columns |
| :--- | :--- | :--- | :--- | :--- |
| `gross_revenue` | Gross Revenue | `ROUND(SUM(total_amount), 2)` | `orders` | `total_amount` |
| `net_revenue` | Net Delivered Revenue | `ROUND(SUM(total_amount), 2) WHERE order_status = 'delivered'` | `orders` | `total_amount`, `order_status` |
| `average_order_value` | Average Order Value (AOV) | `ROUND(AVG(total_amount), 2) WHERE order_status = 'delivered'` | `orders` | `total_amount`, `order_status` |
| `return_rate` | Return Rate | `ROUND(COUNT(returns.return_id) * 100.0 / COUNT(orders.order_id), 2)` | `orders`, `returns` | `returns.return_id`, `orders.order_id` |
| `customer_csat` | Customer Satisfaction Score | `ROUND(AVG(satisfaction_score), 2)` | `support_tickets` | `satisfaction_score` |
| `marketing_roas` | Return on Ad Spend (ROAS) | `revenue / SUM(marketing_spend.spend_amount)` | `orders`, `marketing_spend`, `marketing_channels` | `marketing_spend.spend_amount` |

### 1.3 Missing Semantic Capabilities
- **Dynamic Derivation:** Zero ability to infer new business metrics from unfamiliar schemas.
- **Persistence & User Configuration:** No database table, JSON store, or REST API allows administrators to add, edit, or delete metrics.
- **Formula Portability:** Formulas are raw SQLite SQL expressions; they cannot adapt to other dialect syntaxes or different column names.
- **Validation:** No check validates whether the assumed tables (`returns`, `support_tickets`, `marketing_spend`) actually exist in the currently connected database catalog before injecting them into prompts.

---

## 2. File-by-File Inventory of Domain Coupling

An exhaustive search across the codebase revealed that domain-specific e-commerce assumptions are hardcoded into **8 separate backend modules**:

| Module / File Path | Hardcoded Assumptions | Scope & Impact | Failure Mode on Arbitrary Schema | Severity |
| :--- | :--- | :--- | :--- | :--- |
| [`backend/app/agents/clarification.py#L19-L26`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L19-L26) | `UNSUPPORTED_DOMAINS`: explicitly lists crypto, employee salary, weather, competitor. Statement on line 44 asserts: *"The connected database covers e-commerce operations: orders, customers, products, inventory, marketing, and logistics."* | Global refusal policy in `AnswerabilityGate`. | Legitimate queries on HR or finance schemas are falsely refused as unsupported. | High |
| [`backend/app/agents/clarification.py#L54-L73`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L54-L73) | Hardcoded temporal scope: `val < 2023 or val > 2025` asserts dataset covers strictly Jan 1, 2023 to Dec 31, 2025. | Global refusal policy in `AnswerabilityGate`. | Refuses queries for any other year (e.g. 2020 or 2026) with `OUT_OF_TEMPORAL_SCOPE`. | Critical |
| [`backend/app/agents/clarification.py#L86-L142`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L86-L142) | Clarification options assume YoY (2023 vs 2024), product categories, VIP/Loyal segments, and marketing channels. | Clarification dialogs in `ClarificationAgent`. | Offers invalid clarification choices on non-ecommerce schemas. | Medium |
| [`backend/app/agents/router.py#L107-L160`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/router.py#L107-L160) | Heuristic router assigns `suggested_entities`: `["customer_segment_history", "orders"]`, `["orders", "shipments", "marketing_spend"]`, `["expenses", "inventory", "daily_targets"]`. Line 187 defaults to `["orders"]`. | Fast-path intent classification. | Suggests non-existent entities for unfamiliar schemas. | Medium |
| [`backend/app/retrieval/retriever.py#L11-L50`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L11-L50) | `SYNONYM_TABLE_MAP` contains 50 keyword mappings tied to e-commerce tables: `"revenue": ["orders", "order_items", "payments"]`, `"vip": ["customer_segments", "customers"]`. | Schema grounding in `SchemaGrounder`. | Cannot ground synonyms for tables not in the map. | High |
| [`backend/app/retrieval/retriever.py#L76-L79`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L76-L79) | Fallback table selection: `if not selected: selected.add("orders")`. | Schema grounding in `SchemaGrounder`. | If the database has no `orders` table, downstream SQL generation fails or hallucinates. | Critical |
| [`backend/app/retrieval/corpus.py#L11-L42`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L11-L42) | `DOMAIN_DESCRIPTIONS` dictionary contains 30 hardcoded e-commerce table descriptions. | Document text generation for BM25 and TF-IDF. | Unfamiliar tables receive `"General Operational Data"`, degrading vector retrieval accuracy. | Medium |
| [`backend/app/retrieval/value_linker.py#L19-L48`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/value_linker.py#L19-L48) | `KNOWN_LITERAL_MAPPINGS` hardcodes regexes for segments (VIP, Loyal), order statuses (delivered, cancelled), payment methods (credit card, boleto), promotions (Black Friday). | Categorical entity linking. | Ineffective on non-ecommerce schemas; no dynamic value linking occurs. | Low |
| [`backend/app/retrieval/semantics.py#L20-L69`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L20-L69) | `CANONICAL_METRICS` contains 6 fixed e-commerce metric formulas. | Semantic prompt injection. | Injects invalid SQL formulas into LLM prompt when tables do not exist. | High |
| [`backend/app/analysis/churn.py#L38-L49`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/churn.py#L38-L49) | Hardcoded SQL query referencing `customer_segment_history`, `customer_segments`, `orders`, and columns `csh.valid_to`, `cs.segment_name`. | Deterministic churn analysis tool. | Crashes with `sqlite3.OperationalError: no such table` if segment history table is named differently. | High |
| [`backend/app/workflow/orchestrator.py#L515-L529`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L515-L529) | Orchestrator invokes `simulate_scenario` with hardcoded `baseline_value=1000000.0`, `parameter_name="price"`, and `optimize_budget_allocation` with hardcoded channels `["Search", "Social", "Email", "Affiliate"]`. | Analysis tool execution. | Executes with dummy mock values instead of values parsed from query or database. | Medium |
| [`backend/app/llm/client.py#L83-L106`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/llm/client.py#L83-L106) | `MockLLMProvider._generate_grounded_sql()` hardcodes 8 SQL queries specifically for `ecommerce.sqlite` tables. | Offline / test LLM provider. | Fails on any database other than `ecommerce.sqlite`. | Low |

---

## 3. Real-World Incompatibility Test: `novacart_ecommerce.db`

To verify the impact of domain coupling on a real alternative database, we inspected `novacart_ecommerce.db` (219.8 MB, 46 tables, 2,418,138 rows).

### Verified Failure 1: Deterministic Churn Analysis
- **Expected Table by `churn.py`:** `customer_segment_history`
- **Actual Table in `novacart_ecommerce.db`:** `customer_segments_history` (plural "segments")
- **Execution Result:**
  ```
  Traceback (most recent call last):
    File "backend/app/analysis/churn.py", line 50, in analyze_customer_churn_risk
      cur.execute(query)
  sqlite3.OperationalError: no such table: customer_segment_history
  ```
- **Finding:** `analyze_customer_churn_risk` crashed immediately because the table name differed by a single letter.

### Verified Failure 2: Return Rate Metric Definition
- **Expected Table by `CANONICAL_METRICS["return_rate"]`:** `returns` (column `return_id`)
- **Actual Table in `novacart_ecommerce.db`:** `product_returns` (column `return_id`)
- **Impact:** The injected metric formula `COUNT(returns.return_id)` fails AST validation or query execution against `novacart_ecommerce.db`.

### Verified Failure 3: Marketing ROAS Metric Definition
- **Expected Table by `CANONICAL_METRICS["marketing_roas"]`:** `marketing_spend`
- **Actual Table in `novacart_ecommerce.db`:** `marketing_campaigns` / `marketing_expenses`
- **Impact:** The formula `revenue / SUM(marketing_spend.spend_amount)` refers to a non-existent table.

---

## 4. Architectural Classification of Assumptions

1. **Intentionally Generic:**
   - Period-over-period comparison (`descriptive.py`) — Accepts generic record dicts and column names.
   - Robust anomaly detection (`anomalies.py`) — Accepts generic record dicts, date column, and metric column.
   - Holt-Winters time-series forecast (`forecasting.py`) — Accepts generic chronological record dicts.
   - Driver analysis (`diagnostic.py`) — Accepts generic record dicts and categorical dimension column.
   - Chart specification generator (`visualization.py`) — Automatically derives Plotly bar/line/scatter encodings from SQL result shapes.
2. **Domain-Specific (Hardcoded to E-Commerce):**
   - `CANONICAL_METRICS` (6 metrics)
   - `analyze_customer_churn_risk` (fixed SQL)
   - `KNOWN_LITERAL_MAPPINGS` (25 regex patterns)
   - `DOMAIN_DESCRIPTIONS` (30 tables)
   - `SYNONYM_TABLE_MAP` (50 keywords)
3. **Dataset-Specific (Hardcoded to Synthetic Date Boundaries):**
   - `AnswerabilityGate` temporal range check (`2023 <= year <= 2025`)
   - `ClarificationAgent` Year-over-Year interpretation (`2023 vs 2024`)

---

## 5. Strategic Recommendations for Future Decoupling

Before the platform can achieve true database-agnostic operation, the following refactoring boundary is necessary:
1. **Dynamic Metadata Extraction:** Replace static `DOMAIN_DESCRIPTIONS` with automated LLM-generated table summaries during the onboarding profiling job, stored in database-specific catalog metadata.
2. **Schema-Agnostic Value Linking:** Build the value linker dynamically from the low-cardinality sample values discovered by `SchemaService` during profiling (`dist_cnt <= 10`).
3. **Dynamic Metric Layer:** Implement a database-scoped metric configuration format (e.g. YAML or JSON) where metrics are either user-defined or inferred by LLM and confirmed by an administrator.
4. **Dynamic Temporal Bounds:** Extract minimum and maximum dates dynamically from discovered date columns during profiling rather than hardcoding `2023-2025`.
5. **Generic Churn / Lifecycle Tooling:** Generalize `churn.py` to accept parameters (`segment_table`, `history_table`, `customer_id_col`, `segment_name_col`) rather than executing pre-baked SQL.

