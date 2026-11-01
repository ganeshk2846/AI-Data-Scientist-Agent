# Development History & Audit Trail

## Project Status Matrix

| Phase | Title | Status | Completion Date | Milestone / Deliverables |
|---|---|---|---|---|
| **Phase 0** | Repository and dataset reconnaissance | **Complete** | 2026-11-01 | [DATASET_PROFILE.md](docs/DATASET_PROFILE.md), `scripts/inspect_db.py`, `.gitignore`, `README.md` |
| **Phase 1** | Project foundation and developer experience | **Complete** | 2026-11-01 | FastAPI & Next.js skeletons, health endpoints, test harness |
| **Phase 2** | Read-only database connection & schema preparation | **Complete** | 2026-11-01 | Schema catalogue, profiling service, async preparation job, table inspector UI |
| **Phase 3** | NL question API & first reliable vertical slice | **Complete** | 2026-11-01 | Router, Grounder, sqlglot guardrail, vertical slice chat UI |
| **Phase 4** | Multi-agent workflow, planning & bounded repair | Pending | - | LangGraph orchestration, Router, Planner, Clarification, Verifier |
| **Phase 5** | Hybrid schema retrieval & business semantics | Pending | - | BM25 + embedding RRF, value linking, semantic metrics |
| **Phase 6** | Reliable analysis tools (descriptive, predictive) | Pending | - | Deterministic stats, time-series forecasting, churn risk |
| **Phase 7** | Visualization & business answer composition | Pending | - | Plotly specs, table fallbacks, evidence-linked narrative |
| **Phase 8** | Shared memory, sessions & reusable knowledge | Pending | - | Central MemoryService, session isolation, context pack |
| **Phase 9** | Security, observability, evaluation & performance | Pending | - | AST injection defenses, gold evaluation benchmark, traces |
| **Phase 10** | End-to-end validation & final documentation | Pending | - | Full test suites, developer guide, final sign-off |

---

## Phase 0 — Repository and dataset reconnaissance
- **Date/time:** 2026-11-01T16:45:00+05:30
- **Status:** Complete
- **Objective:** Understand the starting environment, runtime toolchains, and actual SQLite dataset (`ecommerce.sqlite`) before making detailed implementation choices. Verify read-only database connectivity, inventory all tables, columns, constraints, row counts, null rates, and date ranges through executed scripts without making unverified assumptions.
- **Implemented:**
  - Initialized Git repository on `main` and established branch-per-phase workflow (`phase-0-reconnaissance`).
  - Created comprehensive `.gitignore` strictly excluding secrets, environment files, build artifacts, runtime logs, and database binaries.
  - Created `.env.example` providing structured application environment placeholders without exposing credentials.
  - Developed automated read-only database inspection script `scripts/inspect_db.py` utilizing URI mode (`mode=ro`).
  - Developed data quality and relational integrity auditor `scripts/audit_quality.py` checking foreign keys, primary keys, null rates, and financial balances.
  - Generated full profiling data (`docs/dataset_profile_raw.json`) and publication-grade documentation (`docs/DATASET_PROFILE.md`) detailing all 30 tables and 334,503 rows.
  - Established project overview, architecture principles, prerequisites, and setup instructions in `README.md`.
- **Files created/modified:**
  - `.gitignore` (created) — Comprehensive version control exclusion rules.
  - `.env.example` (created) — Configuration template with safe defaults.
  - `README.md` (created) — Architecture, technology stack, setup, and run guide.
  - `DEVELOPMENT_HISTORY.md` (created) — Chronological phase-by-phase implementation log.
  - `scripts/inspect_db.py` (created) — Script for read-only schema introspection.
  - `scripts/audit_quality.py` (created) — Script for auditing foreign keys, nulls, and financial integrity.
  - `scripts/generate_dataset_profile.py` (created) — Markdown generator for dataset profile.
  - `docs/dataset_profile_raw.json` (created) — Machine-readable dataset profile.
  - `docs/DATASET_PROFILE.md` (created) — Comprehensive dataset catalog and quality report.
- **Commands executed:**
  - `python --version; node --version; npm --version; git --version` — Verified runtimes: Python 3.14.7, Node v24.20.0, npm 11.19.0, git version 2.51.1.windows.1.
  - `git init -b main` — Initialized empty Git repository on main branch.
  - `git checkout -b phase-0-reconnaissance` — Created and switched to dedicated Phase 0 branch.
  - `python -m pip list` — Verified pre-installed Python libraries: `fastapi` (0.141.1), `pydantic` (2.13.5), `sqlglot` (30.21.0), `sqlalchemy` (2.1.1), `pandas` (3.0.5), `plotly` (7.1.0), `langgraph` (1.2.12), `scikit-learn` (1.9.0), `statsmodels` (0.15.0), `rank-bm25` (0.2.2), `duckdb` (1.5.6), `xgboost` (3.4.1), `pytest` (9.1.1).
  - `python scripts/inspect_db.py` — Connected to `ecommerce.sqlite` in read-only mode (`mode=ro`), confirmed write block, discovered 30 tables, 0 views, 61 indexes, 44 foreign keys, and 334,503 total rows.
  - `python scripts/audit_quality.py` — Audited relational integrity (`PRAGMA foreign_key_check` returned 0 violations), verified zero duplicate primary keys across all 30 tables, analyzed null rates, and confirmed financial parity.
  - `python scripts/generate_dataset_profile.py` — Generated `docs/DATASET_PROFILE.md` (37,018 bytes).
- **Tests/checks:**
  - Passed: Strict read-only database enforcement check (write probe raised `sqlite3.OperationalError: attempt to write a readonly database`).
  - Passed: Foreign key constraint validation (`PRAGMA foreign_key_check` returned 0 violations across 44 FK declarations).
  - Passed: Primary key uniqueness audit (0 duplicate primary key records found across all 30 tables).
  - Passed: Financial reconciliation sanity check: Delivered gross order amount ($20,891,624.33 across 17,274 orders) equals paid payment amount ($20,891,624.33 across 17,274 payments) exactly. Voided payment amount ($870,344.84 across 650 records) equals cancelled order amount ($870,344.84 across 650 records) exactly.
- **Dataset/schema observations:**
  - Database contains 30 tables and 334,503 rows spanning 2023-01-01 to 2025-12-31 (1,096 consecutive days / 3 full calendar years, including leap year 2024).
  - 7 functional business domains identified:
    1. *Customers & Segments:* 5,000 customers across Brazilian states; longitudinal RFM tiers (`customer_segments`: VIP, Loyal, Occasional, New, At Risk, Dormant).
    2. *Orders & Transactions:* 17,924 orders (17,274 delivered, 650 cancelled) totaling $21,761,969.17 gross; 30,707 order line items.
    3. *Merchandising & Catalog:* 1,000 products, 30 brands, 30 categories, 4 targeted promotions.
    4. *Supply Chain & Warehousing:* 20 warehouses, 24 suppliers, 3,000 purchase orders, 12,960 monthly inventory snapshots.
    5. *Marketing & Attribution:* 8 acquisition channels, 8,768 daily spend records, 71,046 web sessions, 34,640 event actions.
    6. *Post-Purchase & Service:* 2,277 returns, 1,853 refunds, 9,224 customer reviews, 2,174 support tickets.
    7. *Financials & Planning:* 6,576 operating expense records, 1,096 daily targets.
  - Schema naming specifics discovered: Payment monetary value is named `amount` in `payments` (not `payment_amount`).
  - Identified 100% null columns: `daily_targets.channel_id` (targets are enterprise-wide), `expenses.warehouse_id` (expenses are corporate-level), `seller_products.active_to` (all seller listings are currently active).
- **Decisions and rationale:**
  - Architecture adheres strictly to non-use of Redis, Docker, and Kubernetes during development, utilizing local in-process task execution and LangGraph SQLite checkpointing.
  - `ecommerce.sqlite` is maintained as strictly read-only; all agent-owned state and checkpoints will live in a separate writable database (`agent_app.sqlite`).
  - Adopted modular project structure: FastAPI backend in `backend/` and Next.js frontend in `frontend/`.
- **Known issues / limitations:**
  - `orders.channel_id` has a 44.5% null rate, representing unattributed direct traffic or direct organic checkouts; attribution logic must handle null channels gracefully.
  - `website_sessions.customer_id` is 64.5% null, which is standard for top-of-funnel e-commerce traffic where users browse anonymously prior to checkout or account creation.
- **Security/data-safety notes:**
  - Source database access is locked to `mode=ro`.
  - `.gitignore` rigorously prevents accidental check-ins of `.env`, `ecommerce.sqlite`, agent SQLite state, or runtime logs.
- **Next phase:**
  - Phase 1 — Project foundation and developer experience.

---

## Phase 1 — Project foundation and developer experience
- **Date/time:** 2026-11-01T17:05:00+05:30
- **Status:** Complete
- **Objective:** Establish a clean, runnable, testable application skeleton with modular frontend and backend, typed Pydantic configuration, health/readiness endpoints, structured error handling, request ID middleware, safe logging with secret redaction, and an automated test harness.
- **Implemented:**
  - Scaffolded FastAPI backend package (`backend/app`) with typed configuration (`Settings` via `pydantic-settings`).
  - Added strict read-only database connection manager (`backend/app/db/connection.py`) with URI `mode=ro` enforcement and write-probe verification.
  - Implemented structured API response envelopes (`APIResponse[T]`, `ErrorDetail`) and comprehensive exception handlers for domain, HTTP, validation, and generic server errors.
  - Implemented `RequestIdMiddleware` attaching and propagating `X-Request-ID` and timing metrics (`X-Process-Time-Ms`).
  - Implemented safe logging (`SafeFormatter`) with automated regex masking for API keys, tokens, and secrets.
  - Built health and readiness API endpoints:
    - `GET /health` and `GET /api/v1/health` for basic liveness probe.
    - `GET /ready` and `GET /api/v1/ready` for comprehensive multi-dependency readiness (database read-only status, table/row count, LLM configuration status, app store directory readiness).
    - `GET /api/v1/system/status` for safe system diagnostics and configuration metrics.
  - Scaffolded Next.js App Router frontend (`frontend/`) using React, TypeScript, Tailwind CSS, TanStack Query, Lucide icons, and Zod schemas for contract validation.
  - Created responsive frontend dashboard featuring real-time readiness card, architectural pipeline visualization, and domain summaries.
  - Added automated test suites in `backend/tests` covering config, database connection, health probes, and structured error responses.
- **Files created/modified:**
  - `backend/pyproject.toml` (created) — Backend package metadata and pytest configuration.
  - `backend/requirements.txt` (created) — Pinned backend dependencies.
  - `backend/app/main.py` (created) — FastAPI entrypoint, middleware, lifespan, and router mounts.
  - `backend/app/core/config.py` (created) — Pydantic v2 settings with path resolution and secret redaction.
  - `backend/app/core/models.py` (created) — Response envelope, error models, and health/readiness schemas.
  - `backend/app/core/errors.py` (created) — Domain exceptions and unified FastAPI error handlers.
  - `backend/app/core/logging.py` (created) — Secret-masking logger configuration.
  - `backend/app/db/connection.py` (created) — Read-only SQLite connection manager and probe.
  - `backend/app/api/v1/router.py` (created) — Aggregated v1 API router.
  - `backend/app/api/v1/endpoints/health.py` (created) — Health, ready, and status endpoints.
  - `backend/tests/conftest.py` (created) — Pytest fixtures and TestClient setup.
  - `backend/tests/test_config.py` (created) — Tests for configuration and secret redaction.
  - `backend/tests/test_health.py` (created) — Tests for /health, /ready, and /api/v1/system/status.
  - `backend/tests/test_db_connection.py` (created) — Tests for read-only connection, query, and write blocking.
  - `backend/tests/test_errors.py` (created) — Tests for 404 and structured error envelopes.
  - `frontend/package.json` (created) — Next.js, React, Tailwind, TanStack Query, and Zod manifest.
  - `frontend/tsconfig.json` (created) — TypeScript configuration.
  - `frontend/next.config.mjs` (created) — Next.js config with backend API proxy rewrites.
  - `frontend/tailwind.config.ts` (created) — Tailwind CSS styling setup.
  - `frontend/postcss.config.js` (created) — PostCSS plugins.
  - `frontend/src/app/globals.css` (created) — Theme styling and CSS variables.
  - `frontend/src/app/layout.tsx` (created) — Root layout with metadata and TanStack Query provider.
  - `frontend/src/app/providers.tsx` (created) — QueryClientProvider setup.
  - `frontend/src/app/page.tsx` (created) — Interactive readiness and architecture dashboard.
  - `frontend/src/types/api.ts` (created) — Zod runtime schemas and TypeScript interfaces.
  - `frontend/src/lib/api.ts` (created) — API client for readiness probe with Zod validation.
  - `frontend/src/components/Header.tsx` (created) — Application header with backend status badge.
  - `frontend/src/components/HealthReadinessCard.tsx` (created) — Interactive readiness card.
  - `DEVELOPMENT_HISTORY.md` (modified) — Updated status matrix and appended Phase 1 record.
  - `README.md` (modified) — Added local development commands and endpoint documentation.
- **Commands executed:**
  - `git checkout -b phase-1-foundation` — Created dedicated Phase 1 branch.
  - `python -m pytest backend/tests -v` — Ran 12 backend unit/integration tests (all 12 passed in 0.13s).
  - `cd frontend; npm install` — Installed frontend dependencies (added 395 packages in 1m).
  - `cd frontend; npm run build` — Compiled Next.js production build (100% successful with 0 errors).
  - `cd frontend; npm run test` — Verified frontend contract validation scripts.
- **Tests/checks:**
  - Passed: Backend test suite (12/12 passed):
    - `test_settings_defaults`, `test_resolved_paths`, `test_secret_redaction`
    - `test_verify_database_immutability`, `test_readonly_select_query`, `test_readonly_write_blocked`, `test_check_database_readiness`
    - `test_custom_exception_serialization`
    - `test_health_endpoint`, `test_api_v1_health_endpoint`, `test_ready_endpoint`, `test_system_status_endpoint`
  - Passed: Frontend production build (`npm run build`) compiled successfully with static prerendering.
  - Passed: Secret check: `.env.example` has only placeholders; `.gitignore` rigorously prevents secrets, `ecommerce.sqlite`, and build artifacts from tracking.
- **Dataset/schema observations:**
  - Verified live integration with `ecommerce.sqlite` through `check_database_readiness()`: exactly 30 tables and 334,503 rows reported dynamically over the `/ready` API endpoint.
- **Decisions and rationale:**
  - Adopted TanStack Query in frontend for automatic retry and caching of readiness state.
  - Added Next.js API rewrite proxy (`/api/backend/:path*` -> `http://localhost:8000/api/v1/:path*`) to prevent CORS friction during development.
  - Standardized all API error responses on `APIResponse[None]` envelope with machine-readable `code` and correlation `request_id`.
- **Known issues / limitations:**
  - LLM provider runs in mock/unconfigured mode by default until developer provides valid API credentials in `.env`; backend reports this explicitly without blocking server boot.
- **Security/data-safety notes:**
  - `ecommerce.sqlite` is opened strictly with `mode=ro` and verified with a live write probe on startup.
  - `SafeFormatter` strips authorization bearer tokens and API keys from console logs.
- **Next phase:**
  - Phase 2 — Read-only database connection and schema preparation: Building robust schema introspection, catalogue persistence in agent-owned store, idempotent asynchronous preparation jobs, and schema readiness UI.




---

## Phase 2 — Read-only database connection and schema preparation
- **Date/time:** 2026-11-01T17:10:00+05:30
- **Status:** Complete
- **Objective:** Build the trustworthy data foundation. Implement read-only database connection manager, schema introspection and profile generation, idempotent caching in agent store, typed models for tables/columns/PKs/FKs/indexes, asynchronous preparation jobs, and schema readiness UI.
- **Implemented:**
  - Implemented typed schema models (`backend/app/schema/models.py`): `ColumnModel`, `ForeignKeyModel`, `IndexModel`, `TableModel`, `DatabaseCatalog`, `PreparationJobState`, and minimal prompt formatter (`to_minimal_prompt_schema`).
  - Built `SchemaService` (`backend/app/schema/service.py`) for read-only schema introspection, column profiling, distinct/null calculations, date/numeric candidate heuristics, and low-cardinality safe value extraction.
  - Implemented deterministic SHA-256 source fingerprinting (combining file size, mtime, and schema DDL) with idempotent caching in `data/schema_catalog_cache.json`.
  - Built asynchronous `SchemaJobManager` (`backend/app/schema/job.py`) executing non-blocking background preparation jobs in a thread pool executor with live table-by-table progress tracking.
  - Built schema REST API endpoints (`backend/app/api/v1/endpoints/schema.py`):
    - `POST /api/v1/schema/prepare` (trigger preparation with optional force refresh)
    - `GET /api/v1/schema/status` (preparation readiness and catalogue summary)
    - `GET /api/v1/schema/jobs/{job_id}` (progress metrics for specific job)
    - `GET /api/v1/schema/catalog` (full typed catalog payload)
    - `GET /api/v1/schema/tables` (list of table summaries)
    - `GET /api/v1/schema/tables/{table_name}` (detailed table schema and profile)
  - Created interactive frontend schema explorer (`frontend/src/components/SchemaReadinessSection.tsx`):
    - Real-time preparation progress indicator and trigger buttons
    - Searchable table list with row counts and column counts
    - Deep table profile inspector rendering columns, SQLite types, PK/FK/Date badges, null percentages, distinct counts, sample values, and foreign key lineages.
  - Added 10 automated unit and integration tests (`backend/tests/test_schema_service.py`) covering fingerprinting, full database profiling, caching idempotency, minimal prompt formatting, API routes, 404 handling, and temporary test databases.
- **Files created/modified:**
  - `backend/app/schema/__init__.py` (created) — Schema package init.
  - `backend/app/schema/models.py` (created) — Pydantic v2 schema catalogue and job models.
  - `backend/app/schema/service.py` (created) — Read-only introspection and profiling engine.
  - `backend/app/schema/job.py` (created) — Asynchronous preparation job manager.
  - `backend/app/api/v1/endpoints/schema.py` (created) — Schema and catalog REST endpoints.
  - `backend/app/api/v1/router.py` (modified) — Mounted schema router.
  - `backend/tests/test_schema_service.py` (created) — 10 unit and integration tests for schema service.
  - `frontend/src/types/api.ts` (modified) — Added Zod schemas and TypeScript types for catalogue and preparation.
  - `frontend/src/lib/api.ts` (modified) — Added API fetchers for schema status, prepare, tables, and table detail.
  - `frontend/src/components/SchemaReadinessSection.tsx` (created) — Interactive schema preparation and explorer component.
  - `frontend/src/app/page.tsx` (modified) — Integrated `SchemaReadinessSection` into home dashboard.
  - `DEVELOPMENT_HISTORY.md` (modified) — Appended Phase 2 record.
- **Commands executed:**
  - `git checkout -b phase-2-schema-preparation` — Switched to dedicated Phase 2 branch.
  - `python -m pytest backend/tests -v` — Ran 22 backend tests (all 22 passed in 0.82s).
  - `cd frontend; npm run build` — Built frontend production bundle verifying TypeScript contracts and static page generation.
- **Tests/checks:**
  - Passed: Introspection of all 30 tables and 334,503 rows with 44 foreign key declarations against `ecommerce.sqlite`.
  - Passed: Source fingerprint verification (deterministic 64-char hex string).
  - Passed: Minimal prompt schema formatting without leaking sensitive raw values.
  - Passed: REST endpoints `/api/v1/schema/status`, `/tables`, `/tables/orders`, `/catalog`.
  - Passed: Asynchronous job lifecycle and 404 handling on unknown tables.
  - Passed: Temporary database profiling integration test.
  - Passed: Frontend production build (`next build`) compiled with 0 errors.
- **Dataset/schema observations:**
  - Discovered and cataloged safe distinct values for low-cardinality fields: `payments.payment_status` contains only `paid` and `voided`; `orders.order_status` contains `delivered` and `cancelled`; `promotions` contains 4 named promotional events; `customer_segments` contains 6 distinct tiers.
  - Confirmed 0 mutations to `ecommerce.sqlite`.
- **Decisions and rationale:**
  - Used file modification time + size + DDL hash for fingerprinting to detect warehouse changes without scanning all 334k rows.
  - In-process `ThreadPoolExecutor` handles background schema profiling without blocking the asyncio event loop or requiring external workers.
  - Cache is saved to `data/schema_catalog_cache.json` in the application store rather than modifying the source business database.
- **Known issues / limitations:**
  - Large text columns (like support ticket descriptions or review texts) are profiled for null/distinct counts and length without full-text indexing at this stage (lexical BM25 index will be added in Phase 5).
- **Security/data-safety notes:**
  - Full raw table records are never sent to prompt generation; `to_minimal_prompt_schema` emits structural definitions and low-cardinality metadata only.
  - `ecommerce.sqlite` remains strictly read-only (`mode=ro`).
- **Next phase:**
  - Phase 3 — Natural-language question API and first reliable vertical slice: Chat/session APIs, provider-agnostic LLM interface, simple Router, schema-grounded single SQL generation, validation, safe execution, progress states, and results display.


---

## Phase 3 — Natural-language question API and first reliable vertical slice
- **Date/time:** 2026-11-01T17:15:00+05:30
- **Status:** Complete
- **Objective:** Support a complete, trustworthy question-to-answer workflow grounded in real data before adding multi-agent complexity. Implement chat/session APIs, provider-agnostic LLM interface with fallback, simple intent Router, schema Grounder, sqlglot AST validator, read-only SQL execution, result verification, answer composition, observable progress states, and chat UI.
- **Implemented:**
  - Implemented provider-agnostic LLM interface (`backend/app/llm/client.py`, `models.py`) supporting OpenAI, Anthropic, Gemini, and a schema-grounded Mock provider for local/offline testing without external API keys.
  - Implemented `RouterAgent` (`backend/app/agents/router.py`) classifying queries into descriptive, comparative, trend, diagnostic, predictive, or prescriptive intents with recorded confidence score and entity suggestions.
  - Implemented `SchemaGrounder` (`backend/app/retrieval/retriever.py`) mapping business synonyms to real tables and automatically expanding join links via foreign keys.
  - Implemented `SQLValidator` (`backend/app/sql/validator.py`) using `sqlglot` AST parsing to strictly enforce read-only `SELECT` queries, disallow DDL/DML/PRAGMA/multiple statements, verify all table identifiers exist in the schema, and automatically inject row limits.
  - Implemented `SQLExecutor` (`backend/app/sql/executor.py`) executing queries in read-only mode (`mode=ro`) with timeouts and latency measurement.
  - Implemented `QueryWorkflowService` (`backend/app/workflow/service.py`) orchestrating the complete pipeline: Router -> Grounder -> SQL Generator -> AST Validator -> Executor -> Verifier -> Composer, recording step traces and latencies.
  - Built chat REST and SSE streaming endpoints (`backend/app/api/v1/endpoints/chat.py`):
    - `POST /api/v1/chat/query`: Standard synchronous request/response.
    - `POST /api/v1/chat/stream`: Real-time Server-Sent Events (SSE) streaming progress states.
  - Built frontend conversational interface (`frontend/src/components/ChatInterface.tsx`):
    - Input form with quick suggested prompts
    - 7-step pipeline progress stepper
    - Executive business answer card
    - SQL inspector with copy button and timing badge
    - Interactive data results table with formatted values
    - Full step trace timing inspector
  - Added 11 automated unit and integration tests (`backend/tests/test_sql_guardrail.py` and `backend/tests/test_chat_workflow.py`) covering SQL security AST guardrails, router classification, schema retrieval, executor runs, and end-to-end question workflows.
- **Files created/modified:**
  - `backend/app/llm/__init__.py` (created) — LLM package init.
  - `backend/app/llm/models.py` (created) — LLM request/response typed models.
  - `backend/app/llm/client.py` (created) — Provider-agnostic LLM client with Mock provider.
  - `backend/app/agents/__init__.py` (created) — Agents package init.
  - `backend/app/agents/router.py` (created) — Intent and domain router agent.
  - `backend/app/retrieval/__init__.py` (created) — Retrieval package init.
  - `backend/app/retrieval/retriever.py` (created) — Schema grounder and synonym mapper.
  - `backend/app/sql/__init__.py` (created) — SQL safety package init.
  - `backend/app/sql/validator.py` (created) — sqlglot AST validation guardrail.
  - `backend/app/sql/executor.py` (created) — Read-only SQL query runner.
  - `backend/app/workflow/__init__.py` (created) — Workflow package init.
  - `backend/app/workflow/models.py` (created) — Progress state and result models.
  - `backend/app/workflow/service.py` (created) — Vertical slice execution coordinator.
  - `backend/app/api/v1/endpoints/chat.py` (created) — Chat and streaming endpoints.
  - `backend/app/api/v1/router.py` (modified) — Mounted chat router.
  - `backend/tests/test_sql_guardrail.py` (created) — Tests for SQL AST validation rules.
  - `backend/tests/test_chat_workflow.py` (created) — End-to-end question workflow tests.
  - `frontend/src/types/api.ts` (modified) — Added Zod schemas and TypeScript types for chat and workflow results.
  - `frontend/src/lib/api.ts` (modified) — Added `executeChatQuery` API client.
  - `frontend/src/components/ChatInterface.tsx` (created) — Interactive conversational BI component.
  - `frontend/src/app/page.tsx` (modified) — Integrated `ChatInterface` into dashboard.
  - `DEVELOPMENT_HISTORY.md` (modified) — Updated status matrix and appended Phase 3 record.
- **Commands executed:**
  - `git checkout -b phase-3-vertical-slice` — Created dedicated Phase 3 branch.
  - `python -m pytest backend/tests -v` — Ran 33 backend tests (all 33 passed in 0.93s).
  - `cd frontend; npm run build` — Built frontend production bundle with ChatInterface (100% success).
- **Tests/checks:**
  - Passed: SQL AST security validation blocks INSERT, UPDATE, DELETE, DROP, PRAGMA, and multiple statements.
  - Passed: Table identifier hallucination defense (unrecognized table names immediately blocked).
  - Passed: Router classification across descriptive, comparative, trend, and diagnostic questions.
  - Passed: End-to-end question-to-answer execution on live SQLite data (orders by status and revenue).
  - Passed: API endpoint `/api/v1/chat/query` returns correlated `run_id`, sanitized SQL, results table, and composed answer.
  - Passed: Frontend production build (`next build`) compiles without errors.
- **Dataset/schema observations:**
  - Live query verified: `SELECT order_status, COUNT(*), SUM(total_amount) FROM orders GROUP BY order_status;` returns delivered: 17,274 ($20,891,624.33) and cancelled: 650 ($870,344.84) in 1.8ms.
- **Decisions and rationale:**
  - Chose `sqlglot` for AST parsing as it provides deterministic, dialect-aware validation and automated LIMIT enforcement.
  - Implemented MockLLMProvider with schema-grounded SQL generation so that developers without OpenAI/Gemini/Anthropic keys can test the full vertical slice reliably.
  - Progress states are tracked explicitly across 7 discrete stages (`understanding_question`, `retrieving_schema`, `generating_query`, `validating_query`, `running_query`, `verifying_results`, `composing_answer`).
- **Known issues / limitations:**
  - Single-query execution only at this stage; multi-step DAG planning and automatic repair loops will be introduced in Phase 4.
- **Security/data-safety notes:**
  - `ecommerce.sqlite` remains 100% read-only.
  - All SQL queries are strictly validated via AST before hitting the database.
- **Next phase:**
  - Phase 4 — Multi-agent workflow, planning, clarification, and bounded repair: LangGraph workflow orchestration, explicit Router/Planner/Clarification/Visualization agent contracts, DAG execution plans, clarification when ambiguity exists, and bounded 2-attempt SQL repair.
