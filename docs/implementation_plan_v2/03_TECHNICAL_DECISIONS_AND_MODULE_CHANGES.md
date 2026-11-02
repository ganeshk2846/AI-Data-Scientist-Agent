# 03 — Technical Decisions, Module Changes, and API Contracts (Single-Active-DB & Local Ollama Model)

**Target System:** Conversational Data Scientist Agent — AI for Business Intelligence  
**Author Roles:** Principal AI Architect, Senior AI Agent Engineer, Backend Systems Architect  
**Document Lineage:** Final Scope Correction — Single User, One Active Database Connection, One Database Engine at a Time. Real Local LLM (Ollama `qwen3:4b`) and Real Development Database Verification.  
**Execution Boundary:** **STRICT PLANNING ONLY. Architectural Specification. Zero Implementation.**

---

## 1. Architectural Decision Register (ADR)

The following 12 Architectural Decision Records (ADRs) define the technical standards for the platform.

---

### ADR-01: Multi-Engine Connection Abstraction & Driver Selection
- **Decision ID:** `ADR-01`
- **Problem:** Version 1 directly imports Python's `sqlite3` driver, executing SQLite-specific PRAGMAs and lacking all connectivity to PostgreSQL and MySQL.
- **Decision:** Adopt **SQLAlchemy 2.0 Core** connection pooling managing specific, production-grade drivers:
  - **SQLite:** Standard library `sqlite3` (dialect `sqlite+pysqlite`) with URI `mode=ro`.
  - **PostgreSQL:** `psycopg` (v3 `psycopg[binary]>=3.1.18`, dialect `postgresql+psycopg`).
  - **MySQL:** `pymysql` (`pymysql>=1.1.0`, dialect `mysql+pymysql`).
- **Execution Model:** Asynchronous HTTP/SSE gateway with synchronous analytical database queries running in FastAPI's worker thread pool (`fastapi.concurrency.run_in_threadpool`), perfectly aligning with synchronous Pandas `read_sql` and NumPy/SciPy math.
- **Connection Pooling:** `QueuePool(pool_size=3, max_overflow=2, pool_recycle=1800, pool_pre_ping=True)` for active PostgreSQL and MySQL connections; `SingletonThreadPool` or `NullPool` for SQLite.
- **Owner Input Required:** **No.** Concrete drivers and execution models finalized.

---

### ADR-02: Single Active Database Configuration & Identity Storage
- **Decision ID:** `ADR-02`
- **Problem:** Version 1 hardcodes database paths in `.env` / `Settings`. The application needs to support connecting, disconnecting, and reconnecting different engines at runtime without server restart, while remaining strictly single-user.
- **Decision:** **Store Active Database Configuration in `agent_app.sqlite` Table `active_database_config`.**
  - Table stores engine, host, port, dbname, encrypted credentials, connection status, and schema fingerprint.
  - Exactly one row exists representing the active database.
  - When disconnected, status transitions to `DISCONNECTED` and connection pool is disposed.
- **Owner Input Required:** **No.** Simple, robust single-database configuration.

---

### ADR-03: Active Catalog Storage & Fingerprint Invalidation
- **Decision ID:** `ADR-03`
- **Problem:** Catalog caching in V1 used a single static file `data/schema_catalog_cache.json` that was overwritten unpredictably.
- **Decision:** **Store Active Catalog at `data/active_catalog.json` with SHA-256 Fingerprint Tracking.**
  - Atomic rename writes (`.tmp` write then `os.replace`) prevent file corruption.
  - On disconnection, the active catalog is cleared or archived.
  - Cryptographic fingerprinting (`SHA-256` of table names, column counts, DDL timestamps) detects schema drift.
- **Owner Input Required:** **No.** Proven caching pattern.

---

### ADR-04: Persistent Embedded Hybrid Retrieval Architecture
- **Decision ID:** `ADR-04`
- **Problem:** In-memory TF-IDF + BM25 (V1) is ephemeral, losing all indexes on server restart (forcing 14s re-indexing delays) and lacking semantic generalization for synonyms ("turnover" vs "sales"). External vector DBs (Pinecone) introduce unnecessary cloud latency (150ms+) and monthly SaaS costs.
- **Decision:** **Adopt Persistent Embedded Hybrid Retrieval (LanceDB + Disk-Serialized BM25).**
  - **Vector Store:** Single embedded **LanceDB** instance stored at `data/vector_store/` with embedded table `catalog_active`. Zero external microservices, zero cloud costs.
  - **Local Embedding Engine:** Generates 384-dimensional dense vectors using `fastembed` (`sentence-transformers/all-MiniLM-L6-v2`) running via local ONNX runtime in $<15\text{ms}$ on CPU.
  - **Lexical Index:** BM25 token statistics serialized to disk at `data/indexes/active_bm25.pkl`.
  - **RRF Fusion:** Blends lexical BM25 and dense LanceDB ranks with $k=60$.
  - **Persistence:** Indexes survive application restarts; hydrated in $<20\text{ms}$ on boot without re-profiling.
- **Owner Input Required:** **No.** Embedded local vector retrieval finalized.

---

### ADR-05: Three-Tier Semantic Layer & Provenance Architecture
- **Decision ID:** `ADR-05`
- **Problem:** Version 1 hardcodes 6 e-commerce metrics in `CANONICAL_METRICS`. Pure LLM inference risks hallucinating formulas for critical business metrics without user awareness.
- **Decision:** **Implement a Three-Tier Dynamic Semantic Repository in `agent_app.sqlite`:**
  - **Tier 1 (`AUTO_INFERRED`):** Drafted by LLM during onboarding based on column names/samples; marked draft; **never silently used as ground truth for calculations**.
  - **Tier 2 (`VALIDATED_CANDIDATE`):** Passed `sqlglot` AST syntax checks and dry-run query tests; offered as suggested options.
  - **Tier 3 (`USER_APPROVED`):** Explicitly confirmed or edited by the user; injected into generation prompts as authoritative truth.
- **Ambiguity Policy:** Ambiguous metrics (revenue, churn, refunds) trigger interactive clarification or an explicit assumption citation in the executive summary.
- **Owner Input Required:** **No.** Direct resolution of semantic reliability blocker.

---

### ADR-06: Safe Read-Only Enforcement (No Destructive User DB Probes)
- **Decision ID:** `ADR-06`
- **Problem:** Version 1 startup probe attempted `CREATE TABLE __probe__`, which fails on strictly read-only production databases or damages production schemas.
- **Decision:** **Enforce Four Safe Read-Only Layers without Destructive User DB Probes:**
  1. *Least-Privilege Database Credentials:* `GRANT SELECT` only on Postgres/MySQL; `mode=ro` on SQLite.
  2. *Transaction-Level Read-Only Hooks:* `SET TRANSACTION READ ONLY` executed on checkout.
  3. *Dialect AST Inspection:* `sqlglot` blocks DDL, DML, ATTACH, and engine-specific bypasses (`COPY`, `LOAD DATA`).
  4. *Execution Limits & Timeouts:* Injected `LIMIT 1000` + 30-second driver execution timeout.
  - **Write-attempt tests are executed exclusively inside disposable CI test databases, NEVER against user databases.**
- **Owner Input Required:** **No.** Safe, non-destructive read-only enforcement.

---

### ADR-07: Streamlined Five-Stage Asynchronous Onboarding Lifecycle
- **Decision ID:** `ADR-07`
- **Problem:** Version 1 onboarding was synchronous and lacked crash recovery.
- **Decision:** **Consolidate Onboarding into Five Clear Macro-Stages with Persistent Job State:**
  - *Stage 1 (Sync):* Credential Validation & Ping.
  - *Stage 2 (Async):* Structural Introspection & Adaptive Sampling Profiling (sample $N=10,000$ if $>50\text{K}$ rows).
  - *Stage 3 (Async):* Catalog Assembly & Cryptographic Fingerprinting.
  - *Stage 4 (Async):* Persistent Index & Vector Hydration (LanceDB + BM25).
  - *Stage 5 (Async):* Semantic Metric Drafting & Dry-Run Validation.
  - *Job Recovery:* On boot, interrupted jobs are detected via stale heartbeats ($>60\text{s}$) and can be resumed.
- **Owner Input Required:** **No.** Robust single-database onboarding lifecycle.

---

### ADR-08: Database Disconnect & Clean Intelligence Reset
- **Decision ID:** `ADR-08`
- **Problem:** Connecting a new database without clearing old metadata causes schema contamination and hallucinated table references.
- **Decision:** **Atomic Reset of Database-Specific Intelligence upon Disconnection:**
  - Connection pool disposed.
  - `data/active_catalog.json` cleared.
  - LanceDB table `catalog_active` dropped; `data/indexes/active_bm25.pkl` removed.
  - Active semantic metrics truncated.
  - **Zero touch of `agent_app.sqlite` application state, historical sessions, or user databases.**
  - Querying locked until new database onboarding checks succeed.
- **Owner Input Required:** **No.** Complete intelligence isolation across successive connections.

---

### ADR-09: Two-Tier Analytics Framework (Parametric Core + Domain Plugins)
- **Decision ID:** `ADR-09`
- **Problem:** Version 1 mixes generic analytics tools with hardcoded e-commerce scripts (`churn.py`) that crash on schemas with different naming conventions.
- **Decision:** **Separate Universal Core Tools from Schema-Gated Domain Plugins:**
  - *Universal Core Tools:* 100% parametric tools (anomalies, Holt-Winters forecasting, period variance decomposition, SLSQP budget optimization) accepting generic DataFrames + column mappings.
  - *Domain Plugins:* Specialized tools (e.g. churn analysis) that declare explicit required semantic traits and only activate when matching schema entities exist.
- **Owner Input Required:** **No.** Eliminates analytical tool crashes on unfamiliar schemas.

---

### ADR-10: Dialect-Aware SQL Generation & Column-Level AST Validation
- **Decision ID:** `ADR-10`
- **Problem:** Version 1 hardcodes `read="sqlite"` and does not check column existence in the AST against catalog columns.
- **Decision:** **Dialect-Parameterized Generation & Multi-Dialect AST Parsing:**
  - Prompt dynamically injects target engine date functions (`DATE_TRUNC` on Postgres, `DATE_FORMAT` on MySQL, `strftime` on SQLite).
  - `sqlglot.parse_one(sql, read=dialect)` parses AST using active dialect.
  - Extracts all `exp.Column` nodes and verifies column names against active catalog tables.
- **Owner Input Required:** **No.** Resolves dialect and column validation blockers.

---

### ADR-11: Native Ollama `qwen3:4b` Client & Strict No-Mock Runtime Policy
- **Decision ID:** `ADR-11`
- **Problem:** Previous design relied on cloud LLMs (Gemini/OpenAI) or mock responses, failing offline requirements and hiding actual model quality.
- **Decision:** **Implement Dedicated Native Client for Local Ollama (`qwen3:4b`):**
  - Connects to local `http://localhost:11434` via `httpx.AsyncClient`.
  - Configurable via `LLM_PROVIDER=ollama`, `OLLAMA_BASE_URL`, `OLLAMA_MODEL=qwen3:4b`.
  - **Strict No-Mocking Policy:** Mock implementations are strictly barred from runtime, demonstrations, and E2E tests.
  - If Ollama is unavailable, reports a clear diagnostic configuration error.
- **Owner Input Required:** **No.** Concrete local LLM architecture finalized.

---

### ADR-12: Single-User Frontend Connection & Disconnect/Reconnect UX
- **Decision ID:** `ADR-12`
- **Problem:** Frontend has no UI controls to connect, test, or disconnect databases.
- **Decision:** **Single Active Database Frontend Panel:**
  - Engine selection (SQLite, PostgreSQL, MySQL).
  - Connection parameters form (host, port, user, password, db, or file path).
  - Connection test button and real-time onboarding progress stepper.
  - Header status badge showing active engine and `[Disconnect Database]` button.
- **Owner Input Required:** **No.** Clean single-user UX design.

---

## 2. Module-Level Change Plan (Categorized by 6 Subsystems)

| Subsystem | Module / File Path | Current Status | Proposed Change & Scope | Action Type | Dependencies | Phase |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **1. Connection & Discovery** | `backend/app/db/connection.py` | Single SQLite context manager. | Replace with SQLAlchemy 2.0 Core connection manager with `QueuePool`. | **REPLACE** | SQLAlchemy Core | Phase 1 |
| **1. Connection & Discovery** | `backend/app/db/adapters/` *(PROPOSED)* | Does not exist. | Create `base.py`, `sqlite.py` (sqlite3), `postgres.py` (psycopg), `mysql.py` (pymysql). | **NEW** | `connection.py` | Phase 1 |
| **1. Connection & Discovery** | `backend/app/db/active_db.py` *(PROPOSED)* | Does not exist. | Manages active database configuration, connection state, and disconnect/reconnect. | **NEW** | `connection.py` | Phase 1 |
| **1. Connection & Discovery** | `backend/app/schema/introspectors/` *(PROPOSED)*| Embedded in `service.py`. | Create `base.py`, `sqlite.py` (PRAGMAs), `postgres.py` (`information_schema`), `mysql.py`. | **NEW** | `adapters/` | Phase 2 |
| **1. Connection & Discovery** | `backend/app/schema/profiler.py` *(PROPOSED)* | Heavy scans in `service.py`. | Adaptive sampling profiler: sample $N=10,000$ rows on tables $>50\text{K}$ rows; 5s timeout. | **NEW** | `introspectors/` | Phase 2 |
| **2. Metadata & Semantics** | `backend/app/schema/catalog_store.py` *(PROPOSED)*| Single static cache file. | Active catalog store: `data/active_catalog.json` with atomic rename writes and reset. | **NEW** | Pydantic v2 | Phase 2 |
| **2. Metadata & Semantics** | `backend/app/semantics/repository.py` *(PROPOSED)*| Static `CANONICAL_METRICS` dict. | Dynamic 3-tier semantic store (`AUTO_INFERRED`, `VALIDATED_CANDIDATE`, `USER_APPROVED`). | **NEW** | `agent_app.sqlite` | Phase 3 |
| **2. Metadata & Semantics** | `backend/app/retrieval/semantics.py` | Static dictionary. | Refactor to delegate to `SemanticRepository`. | **REFACTOR** | `repository.py` | Phase 3 |
| **3. Hybrid Retrieval** | `backend/app/retrieval/vector_store.py` *(PROPOSED)*| In-memory TF-IDF singleton. | Persistent embedded vector store via **LanceDB** with table `catalog_active`. | **NEW** | `lancedb`, `fastembed`| Phase 3 |
| **3. Hybrid Retrieval** | `backend/app/retrieval/bm25.py` | Ephemeral BM25Okapi. | Retain algorithm; serialize token models to `data/indexes/active_bm25.pkl`. | **ENHANCE** | `rank-bm25` | Phase 3 |
| **3. Hybrid Retrieval** | `backend/app/retrieval/hybrid.py` | Un-scoped global singleton. | Wrap in `PersistentHybridRetriever` combining LanceDB and disk BM25 with RRF ($k=60$). | **REFACTOR** | `vector_store.py` | Phase 3 |
| **3. Hybrid Retrieval** | `backend/app/retrieval/retriever.py` | Fallback to table `"orders"`. | Eliminate hardcoded `"orders"` fallback; return explicit abstention on grounding failure. | **REFACTOR** | `hybrid.py` | Phase 3 |
| **3. Hybrid Retrieval** | `backend/app/retrieval/value_linker.py` | Hardcoded e-commerce regexes. | Dynamically link categorical sample values discovered during data profiling. | **REFACTOR** | `profiler.py` | Phase 3 |
| **4. Safety & Execution** | `backend/app/sql/validator.py` | Hardcoded to SQLite. | Parameterize with `read=dialect`; enforce column existence validation in AST; block bypasses. | **ENHANCE** | `sqlglot` | Phase 2 |
| **4. Safety & Execution** | `backend/app/sql/executor.py` | Static single-file execution. | Execute against active database connection pool; enforce 30s timeout and 1,000 row cap. | **REFACTOR** | `connection.py` | Phase 2 |
| **4. Safety & Execution** | `backend/app/sql/repair.py` | Hardcoded SQLite prompt. | Inject active dialect syntax rules into repair prompt; enforce strict max 2 retries. | **ENHANCE** | `validator.py` | Phase 2 |
| **5. Analytics & Visualization**| `backend/app/analysis/churn.py` | Hardcoded SQL crashing on novacart. | Refactor into schema-aware `ChurnPlugin` requiring user-configured segment tables. | **REFACTOR** | `registry.py` | Phase 4 |
| **5. Analytics & Visualization**| `backend/app/analysis/registry.py` | Mixed generic/hardcoded tools. | Two-tier registry: Universal Core Tools + Schema-Gated Domain Plugins. | **REFACTOR** | `analysis/` | Phase 4 |
| **5. Analytics & Visualization**| `backend/app/agents/visualization.py` | Basic Plotly generation. | Retain core logic; add support for multi-series forecast confidence bands and anomaly markers.| **ENHANCE** | None | Phase 4 |
| **5. Analytics & Visualization**| `backend/app/analysis/` (math files) | MAD, Holt-Winters, SLSQP. | Retain pure mathematical calculations (`anomalies`, `forecasting`, `diagnostic`, `descriptive`). | **RETAIN** | None | Phase 4 |
| **6. Agent Orchestrator** | `backend/app/llm/ollama_client.py` *(PROPOSED)*| Cloud LLM client. | Dedicated async client for local Ollama `http://localhost:11434` running `qwen3:4b`. | **NEW** | `httpx` | Phase 2 |
| **6. Agent Orchestrator** | `backend/app/workflow/orchestrator.py` | Bound to static singleton settings. | Coordinates active subsystems throughout DAG using local Ollama model. | **REFACTOR** | All subsystems | Phase 2 |
| **6. Agent Orchestrator** | `backend/app/agents/clarification.py` | Hardcoded 2023-2025 date check. | Dynamically derive answerability from active catalog tables and discovered date bounds. | **REFACTOR** | `catalog_store.py` | Phase 4 |
| **6. Agent Orchestrator** | `backend/app/agents/router.py` | Hardcodes entity suggestions. | Remove entity suggestions; classify intent purely by analytical structure. | **REFACTOR** | None | Phase 4 |
| **6. Agent Orchestrator** | `backend/app/memory/store.py` | Untracked session database. | Associate sessions with active database fingerprint; preserve on disconnect. | **ENHANCE** | `agent_app.sqlite` | Phase 1 |
| **6. Agent Orchestrator** | `backend/app/memory/service.py` | ContextResolver. | Resolve contextual follow-ups strictly against active database entities. | **ENHANCE** | `store.py` | Phase 1 |
| **Frontend UI** | `frontend/src/app/page.tsx` | Single-database dashboard. | Add active database connection panel, status badge, and disconnect/reconnect controls. | **ENHANCE** | Next.js | Phase 5 |
| **Frontend UI** | `frontend/src/components/Header.tsx` | Static DB indicator. | Add active database engine badge, connection status pill, and Disconnect button. | **ENHANCE** | React | Phase 5 |
| **Frontend UI** | `frontend/src/components/ConnectionPanel.tsx` *(PROPOSED)*| Does not exist. | Engine selector (SQLite, Postgres, MySQL), credentials form, test button, onboarding progress. | **NEW** | React Query | Phase 5 |

---

## 3. Simplified REST & SSE API Contracts (Single Active Database)

### 3.1 Connect Database
- **Endpoint:** `POST /api/v1/database/connect`
- **Request Payload (PostgreSQL / MySQL):**
  ```json
  {
    "engine": "postgresql",
    "host": "localhost",
    "port": 5432,
    "database": "analytics_dw",
    "username": "bi_readonly",
    "password": "SecurePassword123!",
    "ssl_mode": "prefer"
  }
  ```
- **Request Payload (SQLite):**
  ```json
  {
    "engine": "sqlite",
    "file_path": "ecommerce.db"
  }
  ```
- **Response Payload (202 Accepted):**
  ```json
  {
    "engine": "postgresql",
    "database": "analytics_dw",
    "status": "ONBOARDING",
    "job_id": "job_active_20261102",
    "created_at": "2026-11-02T12:00:00Z"
  }
  ```
- **Error Codes:** `400 Bad Request` (connectivity check failed).

### 3.2 Get Active Database Status
- **Endpoint:** `GET /api/v1/database/status`
- **Response Payload (200 OK):**
  ```json
  {
    "connected": true,
    "engine": "sqlite",
    "database_name": "ecommerce.db",
    "status": "READY",
    "tables_count": 46,
    "total_rows": 2418138,
    "fingerprint": "a4f89b...",
    "read_only": true,
    "last_profiled_at": "2026-11-02T12:05:00Z"
  }
  ```

### 3.3 Disconnect Database
- **Endpoint:** `POST /api/v1/database/disconnect`
- **Purpose:** Close connection pool, safely reset database-specific intelligence (catalog, LanceDB collection, BM25 index, semantic metrics), and return to disconnected state.
- **Response Payload (200 OK):**
  ```json
  {
    "status": "DISCONNECTED",
    "message": "Active database disconnected. Intelligence artifacts safely reset. Internal state preserved."
  }
  ```

### 3.4 Poll Onboarding Status
- **Endpoint:** `GET /api/v1/database/onboarding-status`
- **Response Payload (200 OK):**
  ```json
  {
    "job_id": "job_active_20261102",
    "status": "RUNNING",
    "progress_pct": 60,
    "current_stage": "HYDRATING_PERSISTENT_INDEXES",
    "stages_completed": [
      "CREDENTIAL_VALIDATION",
      "STRUCTURAL_INTROSPECTION",
      "ADAPTIVE_SAMPLING_PROFILING",
      "CATALOG_ASSEMBLY"
    ],
    "tables_discovered": 30,
    "error_message": null
  }
  ```

### 3.5 Conversational Query (Direct to Active Database)
- **Endpoint:** `POST /api/v1/chat/stream` (SSE) and `POST /api/v1/chat/query` (REST)
- **Request Payload:**
  ```json
  {
    "query": "Show monthly revenue trends across all regions for 2024",
    "session_id": "sess_8820f4_20261102"
  }
  ```
- **Behavior:** Queries the currently connected active database directly. No `X-Database-ID` header required.

---

*This concludes Document 3 (`03_TECHNICAL_DECISIONS_AND_MODULE_CHANGES.md`). Proceeding to Document 4 (`04_PHASE_WISE_IMPLEMENTATION_ROADMAP.md`).*
