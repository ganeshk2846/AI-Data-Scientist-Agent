# 01 — Executive and Architecture Audit

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Principal Software Architect, Senior AI/ML Engineer, Database Systems Architect, Text-to-SQL Specialist  
**Audit Scope:** Full repository static analysis, architecture trace, and implementation verification. Audit only; zero application code or state modified.

---

## 1. Executive Summary

The audited application is an **AI-powered Text-to-SQL and Conversational Business Intelligence platform** designed to allow business users to ask natural-language questions, inspect database schemas, execute read-only queries, run deterministic statistical and diagnostic calculations, and render Plotly charts.

### High-Level Verdict:
- **Operational Reality:** The application is an advanced, well-engineered prototype tailored around a single read-only SQLite database (`ecommerce.sqlite` / `novacart_ecommerce.db`). It features robust safety guardrails (AST parsing via `sqlglot`, URI `mode=ro`, prompt injection detection), deterministic mathematical models (Holt-Winters forecasting, MAD anomaly screening, variance decomposition), and a hybrid schema retriever (BM25 + TF-IDF with Reciprocal Rank Fusion).
- **Database-Agnostic Reality:** **NOT YET ACHIEVED.** Despite the long-term vision of becoming a universal, dynamic database-agnostic Text-to-SQL agent, the existing Version 1 codebase is **fundamentally single-database and heavily coupled to e-commerce domain schemas and SQLite-specific dialect conventions**.
- **Multi-Database Management:** There is **zero connection registry, zero runtime database switching API, and zero multi-database session isolation**. Database connection paths are loaded from environment variables (`ECOMMERCE_DB_PATH`) into a singleton configuration object (`Settings`).
- **Domain Coupling:** Critical pipeline components—including the `AnswerabilityGate`, `SchemaGrounder`, `ValueLinker`, `CANONICAL_METRICS`, and `analyze_customer_churn_risk`—contain hardcoded table names (`orders`, `customer_segments`, `returns`, `marketing_spend`), fixed temporal boundaries (`2023-2025`), and pre-baked SQL templates. When pointed at a database with a differing schema (such as `novacart_ecommerce.db` where tables are named `customer_segments_history` or `product_returns`), analytical tools and schema grounding fail.

---

## 2. Verified Technology Stack

| Layer | Declared Technology | Actual Verified Version | Primary Source Reference | Architectural Role |
| :--- | :--- | :--- | :--- | :--- |
| **Backend Framework** | FastAPI | `fastapi>=0.110.0` (installed `0.141.1`) | [`backend/app/main.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/main.py) | REST API & SSE streaming server |
| **Application Server**| Uvicorn | `uvicorn[standard]>=0.28.0` | [`backend/requirements.txt`](file:///c:/D_drive/AI_FOR_BI_P/backend/requirements.txt#L2) | ASGI server |
| **Data Validation** | Pydantic v2 | `pydantic>=2.6.0`, `pydantic-settings>=2.2.0` | [`backend/app/core/config.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py) | Typed models, environment parsing |
| **SQL Parser & AST** | SQLGlot | `sqlglot>=23.0.0` (installed `30.21.0`) | [`backend/app/sql/validator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L8) | SQL parsing, read-only AST safety, SQLite transpilation |
| **Database Engine** | SQLite3 | Python standard library `sqlite3` | [`backend/app/db/connection.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L9) | Dual DB architecture (Read-only warehouse + WAL agent store) |
| **Lexical Search** | rank-bm25 | `rank-bm25>=0.2.2` | [`backend/app/retrieval/bm25.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/bm25.py#L7) | BM25Okapi table document scoring |
| **Vector Engine** | Scikit-Learn | `scikit-learn>=1.4.0` | [`backend/app/retrieval/embeddings.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py#L8) | In-memory TF-IDF vectorizer + Cosine Similarity |
| **Analytics Engine** | Pandas & Statsmodels / NumPy | `pandas>=2.2.0`, `statsmodels>=0.14.0`, `scipy` | [`backend/app/analysis/`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/) | Deterministic forecasting, anomalies, optimization |
| **LLM Provider** | Google GenAI SDK | `google-genai>=1.0.0` (Gemini 3.5 Flash Lite) | [`backend/app/llm/client.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/llm/client.py#L112) | Text-to-SQL generation & executive synthesis |
| **Frontend Framework**| Next.js (App Router) | `next 14.2.15` (React 18.3.1, TypeScript 5.4.3) | [`frontend/package.json`](file:///c:/D_drive/AI_FOR_BI_P/frontend/package.json#L17) | Single-Page Application (SPA) dashboard |
| **State & Cache** | TanStack React Query | `@tanstack/react-query ^5.28.9` | [`frontend/src/app/providers.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/app/providers.tsx) | Server-state caching and polling |
| **Visualization** | Plotly.js | `plotly.js-dist-min ^4.2.0` | [`frontend/src/components/PlotlyChartRenderer.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/components/PlotlyChartRenderer.tsx) | Interactive client-side charts |
| **Styling** | Tailwind CSS | `tailwindcss 3.4.1` | [`frontend/tailwind.config.ts`](file:///c:/D_drive/AI_FOR_BI_P/frontend/tailwind.config.ts) | Dark-mode design system |

---

## 3. High-Level Architecture

The system operates as a decoupled client-server architecture:

```
[ User Browser ]
       |
       v
[ Next.js 14 Frontend SPA (Port 3001) ]
       |
       |  REST Calls & Server-Sent Events (SSE)
       v
[ FastAPI Backend Application (Port 8001) ]
       |
       +---> [ Application Router & Endpoints ] (/api/v1/chat, /schema, /ops, /memory)
       |
       +---> [ Multi-Agent Orchestrator ]
       |        |
       |        +---> [ Security Guardrails ] (detect_prompt_injection)
       |        +---> [ ContextResolver ] (Shared Memory in agent_app.sqlite)
       |        +---> [ RouterAgent ] (Classifies Intent: descriptive/trend/etc.)
       |        +---> [ AnswerabilityGate ] (Refuses out-of-scope/unsupported queries)
       |        +---> [ ClarificationAgent ] (Interactive ambiguity resolution)
       |        +---> [ HybridSchemaRetriever ] (BM25 + TF-IDF RRF + FK Graph)
       |        +---> [ LLM Text-to-SQL Generator ] (Gemini 3.5 / OpenAI / Mock)
       |        +---> [ SQLValidator ] (sqlglot AST inspection, mode=ro, limit cap)
       |        +---> [ Bounded Repair Loop ] (Max 2 automated syntax repairs)
       |        +---> [ SQLExecutor ] (Read-only execution against warehouse DB)
       |        +---> [ Result Verifier ] (Sanity & boundary checks)
       |        +---> [ Deterministic Analysis Registry ] (MAD, Holt-Winters, SLSQP)
       |        +---> [ VisualizationAgent ] (Plotly chart specification)
       |        +---> [ Executive Composer ] (Factual markdown answer)
       |
       +---> [ Database Layer ]
                |
                +---> [ Read-Only Warehouse ]: ecommerce.sqlite (mode=ro)
                +---> [ Writable Agent Store ]: agent_app.sqlite (WAL mode)
                +---> [ Catalog Cache File ]: data/schema_catalog_cache.json
```

---

## 4. Application Startup and Execution Lifecycle

### 4.1 Startup Sequence (`backend/app/main.py`)
1. **Settings Loading:** [`Settings`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L18) reads `.env` from repo root. Sets `ECOMMERCE_DB_PATH` (defaults to `ecommerce.sqlite`) and `APP_DB_PATH` (`agent_app.sqlite`).
2. **Lifespan Context Manager:** [`lifespan(app)`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/main.py#L45) fires on FastAPI startup:
   - Executes [`check_database_readiness()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L84).
   - Probes database immutability by executing `CREATE TABLE __probe_violation__` inside `mode=ro` connection to verify write blockage.
   - Computes table and row counts (or loads cached catalog if valid).
   - Checks if LLM API key (`GEMINI_API_KEY` or `OPENAI_API_KEY`) is populated.
3. **Internal Storage Initialized:** [`MemoryStore`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/memory/store.py#L36) and [`ObservabilityTracer`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/observability/tracer.py#L54) execute `CREATE TABLE IF NOT EXISTS` inside `agent_app.sqlite` with `PRAGMA journal_mode = WAL`.
4. **CORS & Middleware:** `RequestIdMiddleware` assigns UUID `X-Request-ID` to all HTTP requests.

### 4.2 End-to-End Question Execution Flow (`MultiAgentOrchestrator`)
When a user submits a natural-language query via `/api/v1/chat/query` or `/api/v1/chat/stream`:

```
User Query: "What is our total revenue for 2024?"
  │
  ├─► [Step -1: Security Screen] (guardrails.py:119)
  │    Check for prompt injection regexes. Blocks immediately if detected.
  │
  ├─► [Step 0: Context Resolution] (memory/service.py:82)
  │    ContextResolver rewrites contextual follow-ups ("what about 2025?") into standalone queries.
  │    Records user turn in agent_app.sqlite.
  │
  ├─► [Step 0.5: Fast-Path Answerability Screening] (clarification.py:29)
  │    AnswerabilityGate screens query against unsupported keywords ("stock price", "crypto")
  │    and temporal range (hardcoded 2023-2025). Fast-refuses if out-of-scope.
  │
  ├─► [Step 1: Intent Routing] (agents/router.py:102)
  │    Router classifies intent ("descriptive", "trend", "comparative", "predictive", etc.).
  │
  ├─► [Step 2: Clarification Check] (agents/clarification.py:80)
  │    If query is ambiguous ("compare revenue"), returns structured clarification options.
  │
  ├─► [Step 3: Hybrid Schema Retrieval] (retrieval/hybrid.py:45)
  │    - Lexical search: BM25Okapi over table documents.
  │    - Dense search: TF-IDF vectorizer + cosine similarity over table descriptions.
  │    - RRF Fusion: Merges ranks with k=60 to pick top 5 tables.
  │    - Foreign Key Graph: Expands join paths (1-hop FK traversal).
  │    - Value Linker: Maps entities ("delivered") to exact database literals.
  │
  ├─► [Step 4: SQL Candidate Generation] (workflow/orchestrator.py:322)
  │    Constructs prompt with minimal schema context, linked values, and metric formulas.
  │    Calls LLM provider (Gemini 3.5 Flash Lite or Mock).
  │
  ├─► [Step 5: SQL AST Validation & Bounded Repair] (sql/validator.py:33 & repair.py:36)
  │    - sqlglot parses AST with read="sqlite".
  │    - Validates single SELECT/UNION statement; blocks DDL/DML, ATTACH, PRAGMA.
  │    - Verifies referenced tables exist in active catalog.
  │    - Injects or caps LIMIT to 1,000 rows.
  │    - If invalid: triggers up to 2 bounded LLM repair attempts.
  │
  ├─► [Step 6: Read-Only Query Execution] (sql/executor.py:28)
  │    Executes validated query on warehouse DB using URI mode=ro with a 30s timeout.
  │    If execution error occurs: triggers bounded execution repair (up to 2 retries).
  │
  ├─► [Step 7: Verification & Bounds Checking] (workflow/orchestrator.py:455)
  │    Checks for empty result sets, result truncation, and execution integrity.
  │
  ├─► [Step 8: Deterministic ML Analysis] (analysis/registry.py:106)
  │    If query intent triggers an analysis tool (e.g. forecast, anomaly, churn),
  │    executes deterministic Python algorithms over returned records.
  │
  ├─► [Step 9: Visualization Specification] (agents/visualization.py:41)
  │    Derives Plotly chart spec (bar, line, scatter, or table fallback).
  │
  ├─► [Step 10: Executive Answer Composition] (workflow/orchestrator.py:538)
  │    LLM summarizes first 10 rows into markdown with direct answers, key findings, and caveats.
  │
  └─► [Step 11: Telemetry & Memory Record] (observability/tracer.py:78)
       Records full trace, latency, SQL, and status in agent_app.sqlite.
```

---

## 5. Architectural Strengths

1. **Dual-Database Safety Isolation:**
   - Business warehouse data is strictly opened via SQLite URI `file:{path}?mode=ro`.
   - The application proactively tests write blockage during startup (`verify_database_immutability`) to confirm write attempts raise `sqlite3.OperationalError`.
   - All mutable state (sessions, turns, telemetry, frames) is segregated into `agent_app.sqlite`.
2. **Deterministic Information Retrieval (RRF):**
   - Combines lexical precision (`rank-bm25`) with semantic similarity (`TfidfVectorizer` + cosine similarity) using standard Reciprocal Rank Fusion ($k=60$).
   - Completely avoids external vector database operational overhead and cloud latency.
3. **Multi-Stage Security Guardrails:**
   - AST validation via `sqlglot` prevents SQL injection, statement chaining, DDL/DML, Cartesian cross-joins, and SQLite extension execution (`load_extension`, `writefile`).
   - Query sanitization injects `LIMIT 1000` automatically.
   - Regex-based prompt injection detection blocks adversarial manipulation before calling the LLM.
4. **Resilient Bounded Repair Loop:**
   - Both AST validation errors and SQLite runtime execution errors trigger an automated repair cycle capped strictly at 2 retries, re-validating repaired queries from scratch.
5. **Deterministic Analytics Guardrails:**
   - Statistical calculations (MAD-based anomaly detection, Holt-Winters exponential smoothing, SLSQP budget allocation) run in pure Python/scipy/pandas, explicitly avoiding hallucinated numbers from generative LLMs.

---

## 6. Confirmed Architectural Weaknesses & Gaps

1. **Strictly Single-Database Architecture:**
   - The application only has one active warehouse connection, determined by `Settings.ECOMMERCE_DB_PATH`.
   - No connection registry, multi-database router, or database identifier exists in the data models.
2. **Global, Single-File Catalog Cache:**
   - Schema profiling saves to a single hardcoded path: `data/schema_catalog_cache.json`.
   - If a different database is mounted, it overwrites the previous database's cache completely.
3. **E-Commerce Domain Assumptions Embedded Across Modules:**
   - `AnswerabilityGate` hardcodes temporal scope strictly to `2023-2025` and lists e-commerce domains.
   - `SchemaGrounder` defaults to selecting `"orders"` if no keyword matches.
   - `ValueLinker` hardcodes literal mappings specifically for e-commerce entities (`vip`, `delivered`, `credit card`, `black friday`).
   - `CANONICAL_METRICS` hardcodes 6 e-commerce metrics referencing tables (`orders`, `returns`, `support_tickets`, `marketing_spend`).
   - `analyze_customer_churn_risk` contains hardcoded SQL referencing `customer_segment_history` and `customer_segments`.
4. **SQLite-Specific Engine Lock-In:**
   - Schema introspection queries use `sqlite_master` and SQLite PRAGMAs (`table_info`, `foreign_key_list`, `index_list`).
   - AST parsing and generation are hardcoded to `read="sqlite"` and `dialect="sqlite"`.
   - Date functions in prompts and helpers use SQLite `strftime()`.
5. **Global Conversation History Lacks Database Scoping:**
   - Conversations stored in `memory_sessions` and `memory_turns` have no `database_id` column.
   - If the user changes the backend database, conversational memory will attempt to resolve follow-ups using context from the previous database.

---

## 7. Readiness Assessment for Database-Agnostic Operation

| Evaluation Dimension | Current Status | Assessment |
| :--- | :--- | :--- |
| **Engine Agnosticism** | **0% Ready** | Strictly coupled to SQLite `sqlite3` connector, PRAGMAs, and SQLite SQL syntax. |
| **Multiple Database Connections** | **0% Ready** | Single static path in `Settings`; no registry or connection manager. |
| **Dynamic Schema Discovery** | **75% Ready** | Profiles tables, columns, PKs, FKs, nulls, and samples dynamically for SQLite. |
| **Retrieval Index Agnosticism** | **50% Ready** | Builds corpus from active catalog, but falls back to hardcoded domain descriptions and keyword maps. |
| **Semantic Layer Agnosticism** | **10% Ready** | Static dictionary of 6 e-commerce metrics; no dynamic metric derivation or registration. |
| **Analytics Reusability** | **60% Ready** | Anomaly, forecasting, and driver tools accept generic record dicts; churn analysis is 100% hardcoded. |
| **Frontend Connection Control** | **0% Ready** | Frontend has no UI to add, switch, or inspect different databases. |

**Summary Conclusion:** Version 1 succeeds as a secure, fast, and feature-rich BI assistant for its built-in dataset, but requires architectural decoupling across connectivity, indexing, semantic metadata, and prompt templates before it can support arbitrary database engines or schemas.

