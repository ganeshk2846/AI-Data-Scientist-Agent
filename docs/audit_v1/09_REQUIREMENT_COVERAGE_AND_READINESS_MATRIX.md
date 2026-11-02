# 09 — Requirement Coverage and Readiness Matrix

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor:** Principal Software Architect & Systems Auditor  
**Evaluation Standard:** Intended Requirement for a Dynamic, Database-Agnostic Text-to-SQL Agent and BI Platform vs. Verified Repository Implementation.

---

## 1. Compliance Status Taxonomy

- **IMPLEMENTED AND VERIFIED:** Fully supported by source inspection, active tests, or completed runtime execution.
- **PARTIALLY IMPLEMENTED:** Mechanism exists in code, but lacks full database-agnostic generality, has hardcoded constraints, or only covers specific subsets.
- **PRESENT BUT NOT VERIFIED:** Source code exists, but was not or could not be demonstrated in safe read-only tests.
- **NOT FOUND:** The feature or architectural capability is completely absent from the codebase.
- **CONTRADICTED BY IMPLEMENTATION:** An earlier claim or documented feature directly conflicts with what the code actually does.
- **NOT APPLICABLE:** Out of scope for this architecture.

---

## 2. Requirement Coverage Matrix

| Capability Area | Audit Evaluation Question | Implementation Status | Evidence & Actual Code Behavior | Architectural Gap / Action Needed for Database-Agnostic Goal |
| :--- | :--- | :--- | :--- | :--- |
| **Generic Connection Layer** | Can the application connect to more than one supported database engine? | **CONTRADICTED BY IMPLEMENTATION** | [`backend/app/db/connection.py:9`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L9): Hardcoded to Python `sqlite3` driver. No adapters, drivers, or connection logic exist for PostgreSQL, MySQL, DuckDB, etc. | Must implement an abstract database connection adapter (e.g. SQLAlchemy 2.0 engine abstraction or async connectors). |
| **Database Registration** | Can several databases be registered and managed simultaneously? | **NOT FOUND** | [`backend/app/core/config.py:50`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L50): Only one static string variable `ECOMMERCE_DB_PATH` is loaded into the `Settings` singleton. | Implement a persistent database connection registry with connection metadata, credentials, and tenant/connection IDs. |
| **Dynamic Schema Discovery** | Are tables and columns discovered from the active database? | **IMPLEMENTED AND VERIFIED** | [`backend/app/schema/service.py:118`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L118): Discovers table names, row counts, column types, PKs, FKs, and indexes from `sqlite_master` and PRAGMAs. | Generalize discovery queries to use ANSI `INFORMATION_SCHEMA` or database-specific introspectors. |
| **Dynamic Schema Profiling** | Can profiles be generated for unfamiliar schemas? | **IMPLEMENTED AND VERIFIED** | [`backend/app/schema/service.py:186-247`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L186-L247): Dynamically profiles null counts, distinct counts, min/max bounds, and safe samples for any table. | Limit expensive `COUNT(DISTINCT)` table scans on multi-million-row databases to sample populations. |
| **Database-Specific Metadata Scoping** | Are metadata artifacts scoped to the correct connection? | **CONTRADICTED BY IMPLEMENTATION** | [`backend/app/schema/service.py:26`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L26): All profiling results are written to a single un-scoped file: `data/schema_catalog_cache.json`. | Key cache files by database fingerprint or UUID: `data/catalogs/{database_id}.json`. |
| **Database-Specific Retrieval Index** | Can indexes be built, selected, persisted, and refreshed independently? | **PARTIALLY IMPLEMENTED** | [`backend/app/retrieval/hybrid.py:40`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L40): Retrieval corpus is built in-memory from active catalog, but index is an un-scoped global singleton. | Store retriever instances in a per-database cache dictionary keyed by `database_id`. |
| **Vector Retrieval** | What retrieval engine is genuinely used? | **IMPLEMENTED AND VERIFIED** | [`backend/app/retrieval/embeddings.py:19`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py#L19): In-memory `scikit-learn` `TfidfVectorizer` + cosine similarity with BM25 Reciprocal Rank Fusion ($k=60$). Zero external vector DBs. | Document and preserve local TF-IDF model, or add optional embedding provider plug-in. |
| **Semantic Layer** | Are definitions dynamically generated, validated, and stored? | **NOT FOUND** | [`backend/app/retrieval/semantics.py:20`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/semantics.py#L20): Static dictionary `CANONICAL_METRICS` with 6 e-commerce metrics. No dynamic generation or persistence. | Build a dynamic semantic layer where metrics can be inferred by LLM, configured via API, and stored per database. |
| **Domain Independence** | Can core features run without fixed e-commerce tables and formulas? | **CONTRADICTED BY IMPLEMENTATION** | Hardcoded e-commerce assumptions in 8 modules: `AnswerabilityGate` (dates 2023-2025), `SchemaGrounder` (defaults to `"orders"`), `churn.py` (crashes on `novacart`), etc. | Eliminate hardcoded table/column strings; replace fallback defaults with genuine abstention or catalog discovery. |
| **Dynamic Relationship Mapping** | Can the platform discover relationships and constrain join selection? | **IMPLEMENTED AND VERIFIED** | [`backend/app/schema/service.py:141`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L141): Introspects foreign keys; `HybridSchemaRetriever` traverses 1-hop FK graph to expand joins. | Add support for inferring implicit join paths when explicit foreign key constraints are not declared in the DDL. |
| **Schema-Grounded SQL Generation** | Does generation use the correct retrieved schema? | **IMPLEMENTED AND VERIFIED** | [`backend/app/workflow/orchestrator.py:326`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L326): `minimal_schema_prompt` injects retrieved tables, column names, PKs, and FKs into the prompt. | Fully functional; operates cleanly with whatever tables are supplied in prompt context. |
| **Dialect-Aware SQL Generation** | Is the actual engine dialect respected throughout generation and validation? | **PARTIALLY IMPLEMENTED** | Prompts and `sqlglot` hardcode `read="sqlite"` and `dialect="sqlite"`. Works for SQLite, fails for other dialects. | Parameterize SQL generation and AST validation by the active connection's detected engine dialect. |
| **Safety Enforcement** | Are read-only rules and permitted identifiers enforced? | **IMPLEMENTED AND VERIFIED** | AST parsing blocks DDL/DML, multi-statements, ATTACH, extensions; connection enforces URI `mode=ro`; verified immutability. | Enforce column-level existence validation in AST in addition to table-level validation. |
| **Database Isolation** | Can identical table names across databases coexist safely? | **NOT FOUND** | Catalogs, sessions, traces, and indexes lack database scoping. Two databases named `customers` collide in cache and memory. | Isolate all state, cache, memory, and telemetry by `database_id`. |
| **Schema-Change Handling** | Are relevant artifacts refreshed when schemas change? | **IMPLEMENTED AND VERIFIED** | [`backend/app/schema/service.py:74`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L74): Computes SHA-256 fingerprint from `st_mtime` and `sqlite_master`; automatically re-profiles if fingerprint changes. | Tested and verified; automatically detects schema modifications and invalidates cache. |
| **Analytics Portability** | Which tools are reusable across arbitrary schemas? | **PARTIALLY IMPLEMENTED** | `compare_periods`, `detect_anomalies`, `analyze_drivers`, and `forecast_series` are generic. `churn.py` is hardcoded. | Generalize `churn.py` to accept table/column arguments or mark it as an optional domain plugin. |
| **Frontend Database Management** | Can users manage connections and select the active database? | **NOT FOUND** | [`frontend/src/app/page.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/app/page.tsx): No database selector, connection modal, or connection status switcher in UI. | Build connection management screen and active database dropdown in header. |
| **Per-Database Conversations** | Are sessions and results associated with the correct database? | **NOT FOUND** | `memory_sessions` and `memory_turns` in `agent_app.sqlite` do not contain a `database_id` column. | Add `database_id` foreign key column to `memory_sessions` and filter sessions by active connection. |
| **Multi-User Behavior** | Is isolation enforced between users and connections? | **PARTIALLY IMPLEMENTED** | `user_id` column exists in `memory_sessions`, but defaults to `"default_user"`. No auth or tenant isolation. | Implement authentication and per-user permission boundaries. |
| **Performance Evidence** | What has actually been benchmarked? | **IMPLEMENTED AND VERIFIED** | AST parse latency (0.86ms p50), Mock end-to-end (18.2ms p50), Gemini end-to-end (1.8s), profiling (3.8s / 14.2s). | Documented with reproducible measurements in `docs/EVALUATION.md`. |
| **Regression Coverage** | Are cross-database scenarios tested? | **CONTRADICTED BY IMPLEMENTATION** | Existing unit tests assert exact row counts (17,924 orders) and table names from `ecommerce.sqlite`. | Build parameterizable test fixtures executing against multiple distinct test databases. |

---

## 3. Readiness Summary Scorecard

| Architectural Pillar | Intended Requirement Target | Current Implementation Level | Readiness Grade |
| :--- | :--- | :--- | :--- |
| **1. Core Connectivity** | Multiple engines (PostgreSQL, MySQL, SQLite, DuckDB) | Single local SQLite file via `sqlite3` connector | **Grade F (0%)** |
| **2. Multi-DB Lifecycle** | Dynamic connection registration, selection, and scoping | Single static path in `Settings` loaded from `.env` | **Grade F (0%)** |
| **3. Schema Discovery** | Dynamic metadata profiling and relationship graphing | Full SQLite profiling; dynamic nulls, bounds, samples | **Grade B+ (85%)** |
| **4. Retrieval & Vector**| Local/external hybrid retrieval, scoped per database | In-memory TF-IDF + BM25 RRF; un-scoped singleton | **Grade B- (70%)** |
| **5. Semantic Layer** | Dynamic metric derivation, validation, and storage | Static dictionary with 6 fixed e-commerce metrics | **Grade D (20%)** |
| **6. SQL Generation** | Dialect-aware, schema-grounded generation & repair | Schema-grounded with 2-step repair; SQLite locked | **Grade B+ (80%)** |
| **7. Safety & Guardrails**| Multi-tier AST parsing, read-only guarantees, timeouts | AST parse (`sqlglot`), URI `mode=ro`, prompt filter | **Grade A (95%)** |
| **8. Analytics Portability**| Reusable statistical calculations across arbitrary data | 4 generic tools (anomalies, forecast, drivers, mix); 1 hardcoded | **Grade B (75%)** |
| **9. Frontend Integration**| Dynamic DB selector, connection manager, chat threads | Single-database dashboard; real-time SSE & Plotly | **Grade C (50%)** |
| **10. Testing & Benchmarking**| Multi-database regression test harness | 100% gold benchmark on single synthetic DB | **Grade B (75%)** |

**Overall Platform Readiness:** **54.5%**  
*The core Text-to-SQL generation, AST validation, hybrid ranking, and deterministic analysis capabilities are solidly engineered, but the foundational architecture remains strictly coupled to a single SQLite database and synthetic e-commerce schema assumptions.*

