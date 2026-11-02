# 10 — Audit Handoff and Open Questions

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Principal Software Architect, Senior AI/ML Engineer, Database Systems Architect  
**Purpose:** Strategic architectural handoff for the project owner, delineating current capabilities, reusable components, hardcoded boundaries, and prioritized design questions prior to embarking on a redesign.

---

## 1. Executive Briefing: What the System Does Today

The existing Version 1 codebase is an advanced, highly responsive, and well-guarded prototype designed for conversational business intelligence over a read-only SQLite database.

### What Works Exceptionally Well:
1. **Safety and Isolation:**
   - Strict read-only database URI enforcement (`mode=ro`) with automated startup write probing.
   - Comprehensive SQL AST inspection via `sqlglot` blocking DDL, DML, ATTACH bypasses, pragma abuse, and dangerous SQLite extensions.
   - Robust prompt-injection regex screening blocking jailbreak attempts before invoking LLMs.
   - Automatic injection of `LIMIT 1000` to prevent memory blowups.
2. **Deterministic Data Analysis (No Hallucinated Math):**
   - Statistical anomaly screening using Median Absolute Deviation (MAD).
   - Time-series trend forecasting with Holt-Winters exponential smoothing and expanding 80%/95% prediction intervals.
   - Deterministic period-over-period variance decomposition along categorical dimensions.
   - Constrained convex budget optimization via `scipy.optimize.minimize` (SLSQP).
3. **Hybrid Schema Grounding:**
   - Fast in-memory fusion of lexical BM25 (`rank-bm25`) and sparse vector cosine similarity (`scikit-learn` `TfidfVectorizer`) using Reciprocal Rank Fusion ($k=60$).
   - Traversal of foreign-key graphs to automatically include necessary join tables.
4. **Resilient User Experience:**
   - Bounded 2-attempt automated query repair loop for syntax and execution errors.
   - Interactive clarification dialogs when queries have multiple interpretations.
   - Shared conversational memory (`ContextResolver`) rewriting follow-ups into standalone queries.
   - Real-time Server-Sent Events (SSE) streaming progress stepper and interactive Plotly chart rendering.

---

## 2. Decoupling Assessment: Dynamic vs. Coupled Components

```
+───────────────────────────────────────+───────────────────────────────────────+
|         GENUINELY DYNAMIC             |         HARDCODED & COUPLED           |
|         (Ready to Reuse)              |      (Must Refactor for Agnosticism)  |
+───────────────────────────────────────+───────────────────────────────────────+
| 1. SQL AST Safety Guardrail           | 1. Database Connection Management     |
|    - Validates read-only SELECT       |    - Fixed to Python sqlite3 connector|
|    - Caches LIMIT 1000                |    - Single path in Settings / .env   |
|                                       |                                       |
| 2. Hybrid Retrieval Algorithm         | 2. Schema Discovery Engine            |
|    - BM25Okapi + TF-IDF RRF           |    - sqlite_master & PRAGMA calls     |
|    - Cosine similarity computation    |                                       |
|                                       | 3. Domain Knowledge & Descriptions    |
| 3. Deterministic Analytics Tools      |    - 30 fixed e-commerce descriptions |
|    - Anomaly detection (MAD)          |    - 50 fixed synonym mappings        |
|    - Trend forecasting (Holt-Winters) |    - 25 regex entity value linkers    |
|    - Period variance decomposition    |                                       |
|                                       | 4. Semantic Layer                     |
| 4. Visualization Specification Agent  |    - CANONICAL_METRICS static dict    |
|    - Inspects SQL output shape        |    - Assumes orders, returns, CSAT    |
|    - Auto-derives Plotly chart spec   |                                       |
|                                       | 5. Analytical Tools                   |
| 5. Bounded SQL Repair Engine          |    - churn.py hardcoded SQL query     |
|    - Recovers from syntax errors      |    - Orchestrator mock arguments      |
|    - Maximum 2 retries                |                                       |
|                                       | 6. Shared Memory & Telemetry          |
| 6. Observability Telemetry Tracer     |    - Zero database-id scoping         |
|    - p50/p95 latency metrics          |    - Single un-scoped catalog cache   |
+───────────────────────────────────────+───────────────────────────────────────+
```

---

## 3. The Core Architectural Bottlenecks

### Bottleneck A: The Single-Database Assumption
- The entire application assumes only **one** business warehouse is mounted at a time.
- Connection parameters are loaded at startup into a global singleton `settings.ECOMMERCE_DB_PATH`.
- **Impact:** To test a second database (like `novacart_ecommerce.db`), the administrator must manually edit `.env` and restart the backend server. There is no runtime connection switcher or multi-tenant database registry.

### Bottleneck B: Un-Scoped Global Caching and State Collisions
- Schema profiling results are persisted to a single hardcoded path: `data/schema_catalog_cache.json`.
- Conversational sessions (`memory_sessions`), chat turns (`memory_turns`), and telemetry traces (`ops_run_traces`) are saved in `agent_app.sqlite` without a `database_id` column.
- **Impact:** Switching databases causes the cache to be completely overwritten. Previous conversational turns referencing old tables leak into context resolution for the new database.

### Bottleneck C: E-Commerce Domain Hardcoding
- The `AnswerabilityGate` rejects queries for dates outside `2023-2025` and explicitly refuses non-ecommerce domains.
- The `SchemaGrounder` defaults to selecting table `"orders"` if no keyword matches.
- `analyze_customer_churn_risk` executes hardcoded SQL expecting `customer_segment_history` and crashes on schemas with differing naming conventions.

---

## 4. Potential Strategic Improvement Areas (For Future Planning)

*Note: In accordance with the audit mandate, no implementation is performed here. These areas represent architectural options for the project owner to consider during future phases:*

### 1. Multi-Engine Connection Layer
- Abstract database connectivity behind a database driver adapter pattern (or SQLAlchemy 2.0 connection engine pool).
- Support connection URI strings: `sqlite:////path/to/db.sqlite`, `postgresql://user:pass@host:port/dbname`, `duckdb:///path/to/db.duckdb`.
- Isolate connection credentials securely.

### 2. Database Registry & Scoped Metadata Store
- Create a `database_connections` table in `agent_app.sqlite` tracking registered databases, active status, engine type, and fingerprint.
- Key catalog caches by database ID: `data/catalogs/{database_id}.json`.
- Scope conversational sessions, frames, and telemetry traces by `database_id`.

### 3. Engine-Agnostic Schema Introspection
- Implement ANSI `INFORMATION_SCHEMA` metadata extraction for PostgreSQL/MySQL, while preserving optimized PRAGMAs for SQLite.
- Sample large tables with bounded row limits during profiling to prevent long startup delays on multi-million-row production databases.

### 4. Dynamic Semantic & Entity Layer
- Replace static `DOMAIN_DESCRIPTIONS` with automated LLM-generated table summaries produced during onboarding and persisted in the catalog cache.
- Extract value linker entities dynamically from low-cardinality categorical samples discovered during profiling.
- Provide a dynamic metric store (JSON/YAML or database table) allowing users and administrators to register, edit, and verify business metric formulas per database.

### 5. Frontend Multi-Database Management
- Add a Database Switcher dropdown to the frontend header.
- Provide a "Connect New Database" modal enabling users to supply connection credentials, initiate asynchronous profiling, monitor progress, and switch active databases seamlessly.

---

## 5. Prioritized Design Questions for the Project Owner

Before designing or implementing Version 2, the following strategic questions must be answered:

1. **Target Database Engine Scope:**
   - *Question:* Which database engines must Version 2 support in production? Is the goal SQLite + PostgreSQL + DuckDB, or should it also encompass MySQL, Snowflake, BigQuery, and SQL Server?
2. **Deployment Topology & Concurrency:**
   - *Question:* Will the system operate as a single-tenant local application (one user analyzing local databases) or as a multi-tenant cloud platform (multiple concurrent users querying different remote enterprise databases)?
3. **Semantic Layer Ownership:**
   - *Question:* Should business metric formulas (e.g., Gross Revenue, Churn, Return Rate) be:
     - (a) Purely inferred dynamically by the LLM from schema column names?
     - (b) Pre-configured by data engineers via a semantic configuration file (e.g. YAML)?
     - (c) Interactively defined and confirmed by the business user through the UI during database onboarding?
4. **Vector Retrieval Infrastructure:**
   - *Question:* The current in-memory TF-IDF + BM25 RRF engine is fast ($<5\text{ms}$) and requires zero external infrastructure. For enterprise schemas with hundreds of tables, should we:
     - (a) Keep the lightweight, local in-memory approach?
     - (b) Introduce a local embedded dense vector store (e.g. LanceDB or Chroma)?
     - (c) Connect to an external enterprise vector database?
5. **Specialized Analytical Tools vs. Generic SQL:**
   - *Question:* Should tools like `analyze_customer_churn_risk` be refactored into generic, parameterizable tools, or should specialized analytical modules be treated as domain-specific plugins enabled only when matching schemas are detected?
6. **Authentication & Access Control:**
   - *Question:* Does the platform require user authentication, role-based access control (RBAC), and column-level data masking, or will all users have identical read-only access to all registered databases?

