# 08 — Complete Findings and Evidence Register

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor:** Principal Software Architect & Codebase Auditor  
**Purpose:** Consolidated master index of verified facts, architectural findings, source code evidence, and artifact inventories.

---

## 1. Master Architectural Findings Register

| ID | Category | Finding Summary | Severity | Status / Confidence | Source File & Line Range | Impact & Affected Modules | Cross-Reference |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **F-01** | Connectivity | **Single-Database Engine Lock-In:** Only SQLite is supported via standard library `sqlite3`. No drivers or connection logic exist for PostgreSQL, MySQL, or DuckDB. | High | **VERIFIED** | [`backend/app/db/connection.py#L9-L48`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L9-L48) | Platform cannot connect to any external relational database engine. | [Report 02: Sec 1-2](02_DATABASE_CONNECTIVITY_AND_ONBOARDING_AUDIT.md) |
| **F-02** | Connectivity | **Zero Multi-Database Management:** The application only loads a single warehouse path from `ECOMMERCE_DB_PATH`. There is no connection registry, switching API, or connection pool. | High | **VERIFIED** | [`backend/app/core/config.py#L50-L53`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L50-L53) | Cannot manage multiple databases simultaneously; requires changing `.env` and restarting server. | [Report 02: Sec 3](02_DATABASE_CONNECTIVITY_AND_ONBOARDING_AUDIT.md) |
| **F-03** | Cache & Isolation| **Un-Scoped Catalog Cache:** Catalog cache is saved to a single static file (`data/schema_catalog_cache.json`). Switching databases overwrites the previous database's cache. | High | **VERIFIED** | [`backend/app/schema/service.py#L26,L88`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L26) | Re-profiling required every time database is switched; cross-database concurrent access corrupts cache. | [Report 02: Sec 6](02_DATABASE_CONNECTIVITY_AND_ONBOARDING_AUDIT.md) |
| **F-04** | Dialect & Engine | **SQLite-Specific Introspection:** Schema profiling relies entirely on `sqlite_master` and PRAGMAs (`table_info`, `foreign_key_list`, `index_list`). | High | **VERIFIED** | [`backend/app/schema/service.py#L118-L172`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L118-L172) | Cannot discover schema metadata on any non-SQLite database. | [Report 02: Sec 7](02_DATABASE_CONNECTIVITY_AND_ONBOARDING_AUDIT.md) |
| **F-05** | Dialect & Engine | **SQLite-Coupled AST & Prompts:** AST parsing (`sqlglot`) and output formatting hardcode `read="sqlite"` and `dialect="sqlite"`. Prompts instruct LLM to use SQLite `strftime()`. | Medium | **VERIFIED** | [`backend/app/sql/validator.py#L62,L107`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L62), [`workflow/service.py#L32`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/service.py#L32) | Incompatible with PostgreSQL/MySQL syntax (`ILIKE`, `::cast`, `INTERVAL`). | [Report 05: Sec 3](05_TEXT_TO_SQL_AND_GUARDRAIL_AUDIT.md) |
| **F-06** | Vector Retrieval | **No Dedicated Vector Database:** Project does NOT use Pinecone, Chroma, Qdrant, Milvus, or FAISS. Uses local in-memory `scikit-learn` TF-IDF + cosine similarity with BM25 RRF ($k=60$). | Medium | **VERIFIED** | [`backend/app/retrieval/embeddings.py#L19-L44`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py#L19-L44) | Zero cloud/vector DB operational overhead; fast ($<5\text{ms}$), but limited to in-memory vocabulary. | [Report 03: Sec 1](03_RETRIEVAL_VECTOR_AND_CACHE_AUDIT.md) |
| **F-07** | Retrieval Isolation| **Ephemeral Un-Scoped Retriever Singleton:** `hybrid_retriever` is a global singleton holding in-memory indexes. Indexes are not scoped by database ID. | Medium | **VERIFIED** | [`backend/app/retrieval/hybrid.py#L126`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L126) | Changing DB path at runtime without re-instantiating leaves stale table index in memory. | [Report 03: Sec 4](03_RETRIEVAL_VECTOR_AND_CACHE_AUDIT.md) |
| **F-08** | Domain Coupling | **Pre-Baked E-Commerce Descriptions & Synonyms:** `DOMAIN_DESCRIPTIONS` (30 tables), `SYNONYM_TABLE_MAP` (50 keywords), and `KNOWN_LITERAL_MAPPINGS` (25 regexes) are hardcoded. | High | **VERIFIED** | [`corpus.py:11`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L11), [`retriever.py:11`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L11), [`value_linker.py:19`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/value_linker.py#L19) | Fails to provide meaningful semantic descriptions or value linking for arbitrary new databases. | [Report 04: Sec 2](04_SEMANTIC_LAYER_AND_DOMAIN_COUPLING_AUDIT.md) |
| **F-09** | Domain Coupling | **Hardcoded Schema Grounder Default:** `SchemaGrounder.retrieve_tables()` defaults to `selected.add("orders")` if no query keywords match. | Critical | **VERIFIED** | [`backend/app/retrieval/retriever.py#L76-L79`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L76-L79) | Downstream SQL generation breaks or hallucinates if a database does not contain a table named `orders`. | [Report 04: Sec 2](04_SEMANTIC_LAYER_AND_DOMAIN_COUPLING_AUDIT.md) |
| **F-10** | Semantic Layer | **Static E-Commerce Metrics:** `CANONICAL_METRICS` contains 6 static e-commerce metrics assuming tables `orders`, `returns`, `support_tickets`, `marketing_spend`. | High | **VERIFIED** | [`backend/app/retrieval/semantics.py#L20-L69`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L20-L69) | Injects invalid SQL metric formulas into prompt when tables do not exist (e.g. in `novacart_ecommerce.db`). | [Report 04: Sec 1](04_SEMANTIC_LAYER_AND_DOMAIN_COUPLING_AUDIT.md) |
| **F-11** | Domain Coupling | **Hardcoded Temporal Scope & Domains:** `AnswerabilityGate` hardcodes `val < 2023 or val > 2025` and e-commerce domains, refusing valid queries outside this window. | Critical | **VERIFIED** | [`backend/app/agents/clarification.py#L19-L73`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L19-L73) | Automatically refuses queries for dates outside 2023-2025 or domains like HR, healthcare, or logistics. | [Report 04: Sec 2](04_SEMANTIC_LAYER_AND_DOMAIN_COUPLING_AUDIT.md) |
| **F-12** | Analytics Coupling | **Hardcoded Churn Analysis Tool:** `analyze_customer_churn_risk` executes hardcoded SQL referencing `customer_segment_history` and `customer_segments`. | High | **VERIFIED** | [`backend/app/analysis/churn.py#L38-L49`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/churn.py#L38-L49) | Verified crash on `novacart_ecommerce.db` (`sqlite3.OperationalError: no such table: customer_segment_history`). | [Report 04: Sec 3](04_SEMANTIC_LAYER_AND_DOMAIN_COUPLING_AUDIT.md) |
| **F-13** | Analytics Mocking | **Hardcoded Scenario & Budget Arguments:** `simulate_scenario` and `optimize_budget_allocation` are dispatched with hardcoded dummy inputs (`baseline=1000000`, channels `["Search", "Social"]`). | Medium | **VERIFIED** | [`backend/app/workflow/orchestrator.py#L515-L529`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L515-L529) | Analytics results do not reflect values parsed from user query or warehouse data. | [Report 06: Sec 1](06_ANALYTICS_FRONTEND_AND_INTEGRATION_AUDIT.md) |
| **F-14** | Shared Memory | **Conversation History Lacks Database Scoping:** Sessions in `memory_sessions` and turns in `memory_turns` do not record a `database_id` column. | Medium | **VERIFIED** | [`backend/app/memory/store.py#L42-L61`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/memory/store.py#L42-L61) | Switching databases leaks previous database context into follow-up query resolutions. | [Report 06: Sec 5](06_ANALYTICS_FRONTEND_AND_INTEGRATION_AUDIT.md) |
| **F-15** | Observability | **Global Un-Scoped Telemetry:** Traces table `ops_run_traces` lacks a `database_id` column; metrics are globally aggregated across all runs. | Low | **VERIFIED** | [`backend/app/observability/tracer.py#L59-L71`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/observability/tracer.py#L59-L71) | Cannot compute per-database performance or error percentiles. | [Report 07: Sec 4](07_TESTING_PERFORMANCE_SECURITY_AND_RELIABILITY.md) |
| **F-16** | Frontend | **Zero Database Connection Interface:** Frontend has no UI component, dropdown, modal, or form to register, select, or configure database connections. | High | **VERIFIED** | [`frontend/src/app/page.tsx#L71-L96`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/app/page.tsx#L71-L96) | User cannot interact with multiple databases from the UI. | [Report 06: Sec 2-3](06_ANALYTICS_FRONTEND_AND_INTEGRATION_AUDIT.md) |
| **F-17** | Testing | **Unit Tests Bound to Synthetic Dataset:** Tests in `backend/tests/` assert exact row counts (17,924 orders, 334,503 total rows) from `ecommerce.sqlite`. | Medium | **VERIFIED** | [`backend/tests/test_db_connection.py#L25,L41`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_db_connection.py#L25) | Test suite fails if run against any other database. | [Report 07: Sec 1](07_TESTING_PERFORMANCE_SECURITY_AND_RELIABILITY.md) |
| **F-18** | Security | **Robust Multi-Layer Security Guardrails:** AST parsing blocks DDL/DML; prompt injection regex blocks jailbreaks; URI `mode=ro` physically prevents disk writes. | Positive | **VERIFIED** | [`sql/validator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py), [`security/guardrails.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/security/guardrails.py), [`db/connection.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py) | 100% attack rejection rate measured on gold benchmark. | [Report 05: Sec 3](05_TEXT_TO_SQL_AND_GUARDRAIL_AUDIT.md) |
| **F-19** | Reliability | **Resilient Bounded Repair Loop:** Max 2 automated SQL repair retries on AST syntax errors or runtime SQLite operational errors. | Positive | **VERIFIED** | [`backend/app/sql/repair.py#L36-L91`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/repair.py#L36-L91) | High repair success rate; prevents infinite retry loops. | [Report 05: Sec 4](05_TEXT_TO_SQL_AND_GUARDRAIL_AUDIT.md) |
| **F-20** | Architecture | **Generic Portable Analytics Tools:** Anomaly detection (MAD), time-series forecasting (Holt-Winters), and driver analysis (variance decomposition) accept generic record dicts. | Positive | **VERIFIED** | [`anomalies.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/anomalies.py), [`forecasting.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/forecasting.py), [`diagnostic.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/diagnostic.py) | Fully reusable across arbitrary database schemas. | [Report 06: Sec 1](06_ANALYTICS_FRONTEND_AND_INTEGRATION_AUDIT.md) |

---

## 2. Inventory of Critical Symbols and Artifacts

### 2.1 Important Backend Classes & Functions
- **Settings:** [`backend.app.core.config.Settings`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L18) — Singleton configuration manager.
- **Connection Context:** [`backend.app.db.connection.get_readonly_connection`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L24) — Read-only SQLite context manager.
- **Immutability Probe:** [`backend.app.db.connection.verify_database_immutability`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L50) — Startup write-block verification.
- **Schema Service:** [`backend.app.schema.service.SchemaService`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L29) — Introspects, profiles, fingerprints, and caches schema.
- **Job Manager:** [`backend.app.schema.job.SchemaJobManager`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/job.py#L15) — Background task runner for non-blocking profiling.
- **Hybrid Retriever:** [`backend.app.retrieval.hybrid.HybridSchemaRetriever`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L36) — Fuses BM25 and TF-IDF cosine similarity via RRF.
- **TF-IDF Retriever:** [`backend.app.retrieval.embeddings.LocalTFIDFEmbeddingRetriever`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py#L19) — In-memory sparse vector retriever.
- **BM25 Retriever:** [`backend.app.retrieval.bm25.BM25Retriever`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/bm25.py#L11) — Lexical document retriever.
- **Value Linker:** [`backend.app.retrieval.value_linker.ValueLinker`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/value_linker.py#L51) — Entity literal linker.
- **Semantic Registry:** [`backend.app.retrieval.semantics.SemanticRegistry`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L72) — Business metric formulas registry.
- **Router Agent:** [`backend.app.agents.router.RouterAgent`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/router.py#L96) — Intent and complexity classifier.
- **Planner Agent:** [`backend.app.agents.planner.PlannerAgent`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/planner.py#L12) — Builds typed 7-step execution DAG.
- **Answerability Gate:** [`backend.app.agents.clarification.AnswerabilityGate`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L29) — Evaluates question domain and temporal scope.
- **Clarification Agent:** [`backend.app.agents.clarification.ClarificationAgent`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/clarification.py#L80) — Interactive ambiguity resolver.
- **Visualization Agent:** [`backend.app.agents.visualization.VisualizationAgent`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/agents/visualization.py#L38) — Derives typed Plotly specifications.
- **SQL Validator:** [`backend.app.sql.validator.SQLValidator`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L27) — AST parser, identifier verifier, and row-limit injector.
- **SQL Repair Loop:** [`backend.app.sql.repair.SQLRepairLoop`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/repair.py#L36) — Bounded 2-attempt query repair engine.
- **SQL Executor:** [`backend.app.sql.executor.SQLExecutor`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/executor.py#L25) — Read-only execution runner with 30s timeout.
- **Multi-Agent Orchestrator:** [`backend.app.workflow.orchestrator.MultiAgentOrchestrator`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L103) — Full pipeline coordinator.
- **Memory Service:** [`backend.app.memory.service.MemoryService`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/memory/service.py#L24) — Shared conversational memory and ContextResolver.
- **Observability Tracer:** [`backend.app.observability.tracer.ObservabilityTracer`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/observability/tracer.py#L41) — Telemetry recorder and percentile calculator.

### 2.2 Environment Variables Inventory
- `APP_ENV` (defaults to `"development"`)
- `APP_DEBUG` (defaults to `False`)
- `APP_HOST` (defaults to `"0.0.0.0"`)
- `APP_PORT` (defaults to `8001`)
- `LOG_LEVEL` (defaults to `"INFO"`)
- `ECOMMERCE_DB_PATH` (defaults to `"ecommerce.sqlite"`)
- `APP_DB_PATH` (defaults to `"agent_app.sqlite"`)
- `LLM_PROVIDER` (defaults to `"mock"`, options: `gemini`, `openai`, `anthropic`, `mock`)
- `GEMINI_API_KEY` / `GEMINI_MODEL` (`"gemini-3.5-flash-lite"`)
- `OPENAI_API_KEY` / `OPENAI_MODEL` (`"gpt-4o-mini"`)
- `ANTHROPIC_API_KEY` / `ANTHROPIC_MODEL` (`"claude-3-5-sonnet-20241022"`)
- `SQL_QUERY_TIMEOUT_SECONDS` (defaults to `30`)
- `SQL_MAX_ROWS_RETURN` (defaults to `1000`)
- `NEXT_PUBLIC_API_URL` (frontend endpoint, defaults to `http://localhost:8001`)

### 2.3 Generated Files & Local State Artifacts
- `data/schema_catalog_cache.json` — Un-scoped schema metadata cache.
- `agent_app.sqlite` — Application state database (tables: `memory_sessions`, `memory_turns`, `memory_preferences`, `memory_exemplars`, `ops_run_traces`).
- `ecommerce.sqlite` — 47.4 MB synthetic database (30 tables, 334,503 rows).
- `novacart_ecommerce.db` — 219.8 MB alternative database (46 tables, 2,418,138 rows).
- `docs/EVALUATION.md` — Benchmark test results output.

