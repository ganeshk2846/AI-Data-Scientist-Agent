# AI for BI Data Scientist Agent — System Architecture Document

## 1. System Overview & Core Philosophy

The **AI for BI Data Scientist Agent** is an enterprise-grade conversational business intelligence and analytics system designed to operate directly against relational data warehouses without mutating source databases, hallucinating schemas, or trusting ungrounded LLM calculations.

The reference dataset is **`ecommerce.sqlite`**, a rich 30-table, 334,503-row retail and logistics data warehouse covering January 1, 2023 through December 31, 2025.

### Foundational Invariants:
1. **Source Immutability:** `ecommerce.sqlite` is opened exclusively in read-only URI mode (`mode=ro`). No migrations, temporary tables, or DDL/DML ever execute against the business warehouse.
2. **Deterministic Calculation:** LLMs are never asked to perform arithmetic, statistics, or predictions. All calculations, variance decompositions, forecasts, and churn risk scoring execute in pure, unit-tested Python functions.
3. **AST Guardrail Security:** Every generated SQL statement is parsed and validated using `sqlglot` prior to execution. Statements containing DDL, DML, ATTACH, DETACH, PRAGMAs, dangerous functions, or unconstrained Cartesian cross joins are blocked.
4. **ContextResolver:** Multi-turn memory follows the principle *"Rewrite, don't concatenate"*. Downstream retrieval, planning, and SQL generation components always receive clean, standalone questions.
5. **Separation of Concerns:** Application state, sessions, preferences, and telemetry reside in an agent-owned store (`agent_app.sqlite`).

---

## 2. Multi-Agent Pipeline Architecture

```
User Natural Language Question
              │
              ▼
   ┌──────────────────────┐
   │    ContextResolver   │ ◄── [Shared MemoryService in agent_app.sqlite]
   └──────────┬───────────┘
              │ (Rewritten Standalone Query)
              ▼
   ┌──────────────────────┐
   │     Router Agent     │ ─── Intent (Descriptive, Comparative, Trend, Churn, Forecast)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │  Answerability Gate  │ ─── Refuses Out-of-Scope (Crypto, Dates outside 2023-2025)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ Clarification Policy │ ─── Detects Ambiguities & Generates Structured Alternatives
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │     Planner Agent    │ ─── Decomposes Query into 7-Step Dependency DAG
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │   Hybrid Retriever   │ ─── BM25 + TF-IDF RRF (k=60) + 1-Hop FK Expansion + Value Linker
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │    SQL Generator     │ ─── Generates Minimal SQLite Query
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ AST Security & Repair│ ─── sqlglot Guardrail & Bounded 2-Attempt Repair Loop
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │  Read-Only Executor  │ ─── Runs on ecommerce.sqlite (mode=ro, Row Limits)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ Deterministic Tools  │ ─── Trend Decomp, MAD Anomalies, Holt-Winters, SLSQP Optimizer
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │  Visualization Agent │ ─── Derives Typed Plotly Specs (Line, Bar, Pie, Table Fallback)
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │  Executive Composer  │ ─── Factual Narrative, Key Findings, Citations, Next Questions
   └──────────┬───────────┘
              ▼
   ┌──────────────────────┐
   │ Observability Tracer │ ─── Records Telemetry, Latency (p50/p95), & Cost in agent_app.sqlite
   └──────────────────────┘
```

---

## 3. Core Subsystems

### 3.1 Schema Grounding & Hybrid Retrieval
- **Schema Corpus:** Generates rich textual representations for all 30 tables combining column names, types, foreign key join paths, and domain descriptions.
- **Reciprocal Rank Fusion (RRF, $k=60$):** Combines lexical BM25 precision with local TF-IDF semantic embedding cosine similarity.
- **Foreign Key Graph Expansion:** Automatically traverses relational edges to include bridge tables required for joins (e.g. bridging `orders` to `products` via `order_items`).
- **Low-Cardinality Value Linker:** Extracts entity values (e.g., `"delivered"`, `"credit_card"`, `"VIP"`) and maps them to exact column equality filters.

### 3.2 SQL Safety Guardrails & Bounded Repair
- **AST Visitor:** Built on `sqlglot`. Only `SELECT` and `UNION` AST expressions are permitted.
- **Blacklists:** Keyword and token filters block `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `ATTACH`, `DETACH`, `PRAGMA`, and SQLite functions `LOAD_EXTENSION`, `WRITEFILE`, `READFILE`, `EDIT`.
- **Cost Guard:** Rejects unconstrained Cartesian cross joins without join conditions.
- **Bounded Repair Loop:** If an initial SQL draft fails AST validation or runtime syntax checks, the error message and schema context are fed back for at most 2 repair attempts. If repair fails, the system fails safe.

### 3.3 Deterministic Analysis Toolkit
- **Period-over-Period Comparison:** Exact mathematical delta and percentage change with categorical mix attribution.
- **MAD Anomaly Detection:** Uses Median Absolute Deviation ($z = 0.6745 \times \frac{x - \text{median}}{\text{MAD}}$) with pre-flight screening for duplicate batch loads and missing timestamp gaps.
- **Diagnostic Driver Analysis:** Decomposes total metric variance across dimensions with sample sizes and explicit non-causal disclaimers.
- **Time-Series Forecasting:** Evaluates seasonal naive and exponential smoothing baselines with holdout backtesting (MAE, RMSE, MAPE) and 80%/95% prediction intervals. Abstains if $n < 10$.
- **What-If Simulation:** Log-log elasticity simulation with sensitivity spectrum analysis.
- **Churn Risk & Prioritization:** Analyzes active segments from `customer_segment_history`, calculates Wilson score 95% confidence intervals, and ranks segments by expected revenue at risk.
- **Prescriptive Optimization:** Uses `scipy.optimize` (SLSQP) to allocate marketing budgets across channels with diminishing returns under linear budget bounds.

### 3.4 Visualization & Answer Composition
- **Plotly.js Renderer:** Renders responsive dark-themed charts dynamically in the Next.js frontend with PNG export controls.
- **Rule-First Chart Selection:** Time series -> Line; Categorical ranking -> Bar; Low-cardinality status distribution -> Donut Pie; Scalar/Text -> Table fallback.
- **Executive Composer:** Produces structured business narratives with citations, data coverage caveats, and 3 clickable follow-up analytical questions.

### 3.5 Shared Memory & Observability
- **Agent Store (`agent_app.sqlite`):** Isolates session turns, active frames, preferences, and run traces from the read-only business database.
- **ContextResolver:** Rewrites follow-up inquiries (e.g. "What about 2025?") into standalone queries without polluting downstream agents with raw transcripts.
- **Telemetry:** Captures p50, p95, p99 latencies, success rates, and redacts PII/secrets.

