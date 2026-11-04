# AI for BI — Complete Project Architecture Documentation
## Conversational Data Scientist Agent

**Document Reference:** `docs/architecture/COMPLETE_PROJECT_ARCHITECTURE.md`  
**Git Branch:** `integration/frontend-final`  
**Git Commit:** `2bfa343`  
**Target Audience:** Enterprise Software Architects, AI Systems Engineers, Database Performance Engineers, Technical Reviewers  
**Companion Diagrams:** `docs/architecture/*.mmd` (Draw.io compatible via Arrange -> Insert -> Advanced -> Mermaid)

---

## 1. Project Overview

The **AI for BI — Conversational Data Scientist Agent** is an enterprise-grade analytical intelligence platform that converts natural language business inquiries into schema-grounded SQL queries, deterministic statistical calculations, time-series machine learning forecasts, what-if simulations, and executive decision-support briefings.

### Architectural Philosophy
1. **Separation of Reasoning and Computation:** Large Language Models (Groq Cloud API) are utilized strictly for question understanding, query translation, and executive narrative synthesis. All arithmetic, trend aggregations, statistical significance evaluations, time-series forecasting, and budget optimizations are executed by **deterministic Python analytical engines** (Pandas, SciPy, statsmodels, LightGBM).
2. **Schema-Grounded Accuracy:** SQL queries are strictly constrained to tables and columns discovered through hybrid retrieval (BM25 + LanceDB dense vectors + Reciprocal Rank Fusion) and validated via `sqlglot` Abstract Syntax Tree (AST) parsing prior to execution.
3. **Database Read-Only Safety:** Warehouse connections are locked into read-only transaction parameters with zero capability to modify data.
4. **Domain Independence:** The system does not hardcode business schemas or eCommerce assumptions; it discovers relations dynamically through metadata introspection and cryptographic fingerprinting.

---

## 2. High-Level System Architecture
*(Companion Diagrams: Level 1 [`01_system_context.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/01_system_context.mmd) and Level 2 [`02_high_level_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_high_level_application_architecture.mmd))*

The application is structured as a multi-tier decoupled architecture:
1. **Frontend Presentation Tier (Next.js 14 / React 18):** Modern responsive web application utilizing Tailwind CSS, Lucide icons, dynamic Plotly.js charts, and Server-Sent Events (SSE) streaming progress steppers.
2. **API Gateway & Routing Tier (FastAPI):** Asynchronous ASGI gateway providing REST and SSE endpoints with CORS protection, monotonic request tracing, and exception translation.
3. **Multi-Agent Orchestration Tier:**
   - **`MultiAgentOrchestrator` (`workflow_orchestrator`):** Direct conversational BI chat and rapid Text-to-SQL pipeline.
   - **`AgenticSupervisor` (`agentic_supervisor`):** Multi-specialist autonomous decision-support engine.
4. **Hybrid Retrieval Tier:** Dual-channel schema search fusing BM25 lexical precision and FastEmbed dense vector embeddings via Reciprocal Rank Fusion (RRF, $k=60$), foreign-key graph traversal, and fuzzy literal value linking.
5. **Deterministic Analytical Engines Tier:** 7 PRD business analytical categories executed in pure Python with mathematical verification.
6. **Multi-Engine Database Tier:** Read-only adapters for SQLite, PostgreSQL, and MySQL, alongside an operational SQLite store (`agent_app.sqlite`) for observability traces, spans, and conversational memory.
7. **LLM Inference Tier:** Exclusive single-provider integration with the **Groq Cloud API** running open-weight high-parameter models on Language Processing Units (LPUs).

---

## 3. Frontend Structure & Application Shell
*(Companion Diagram: [`02_frontend_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_frontend_application_architecture.mmd))*

The frontend is implemented using the Next.js 14 App Router:
* **AppShell (`frontend/src/components/AppShell.tsx`):** Provides top-level workspace layout, unified navigation header, and quick switching between primary functional views:
  1. **Overview (`/`):** Strategic executive briefing with interactive 3D hero visualization (`Hero.tsx`, `HeroScene.tsx`, `HeroPlot.tsx`).
  2. **Conversational BI Workspace (`/`):** Interactive chat turn execution (`ChatInterface.tsx`), prompt input (`ChatInput.tsx`), animated SSE progress stepper (`StreamingStepper.tsx`), management narrative (`AnswerView.tsx`), and tabbed evidence panel (`EvidencePanel.tsx`).
  3. **Activity / Observability (`/activity`):** Historical run telemetry, p50/p95/p99 latency cards, and execution trace tables (`ObservabilityDashboard.tsx`).
  4. **Catalog Explorer (`/catalog`):** Relational schema browser displaying tables, row cardinalities, and column profiles (`SchemaReadinessSection.tsx`).
  5. **System Screen (`/system`):** Diagnostic health status, database readiness, and active connection indicators (`SystemScreen.tsx`, `HealthReadinessCard.tsx`).
* **Onboarding & Setup Routes:**
  - `/connect/llm`: Secure entry form for Groq API key and model selection (`GroqConnectionForm.tsx`).
  - `/connect/database`: Database URI connection form and drag-and-drop SQLite file uploader (`DatabaseConnectionForm.tsx`).
  - `/setup/preparing`: 7-stage schema preparation job progress tracker (`PreparationProgress.tsx`).
  - `/settings/connections`: Tabbed connection management for switching active database or LLM (`ConnectionManager.tsx`).
* **Route Guard (`SetupReadinessGuard.tsx`):** Intercepts client navigation on application startup, verifies readiness via `GET /api/v1/ready`, and redirects unconfigured sessions to the self-service setup flow.

---

## 4. Backend Structure & API Routing

The backend is built with FastAPI (`backend/app/main.py`) following clean architectural boundaries:
* **`backend/app/core/`:** Configuration (`config.py`), error definitions (`errors.py`), structured logging (`logging.py`), and base contracts (`contracts.py`).
* **`backend/app/api/v1/router.py`:** Aggregates all modular controllers under the `/api/v1` prefix:
  - `/chat`: Interactive conversational chat queries and SSE streaming (`endpoints/chat.py`).
  - `/agentic`: Agentic multi-specialist supervisor queries and SSE streaming (`endpoints/agentic.py`).
  - `/schema`: Relational catalog introspection and preparation job triggers (`endpoints/schema.py`).
  - `/database`: Connection testing, active database switching, and file uploads (`endpoints/database.py`).
  - `/llm`: Groq connection testing and model discovery (`endpoints/llm.py`).
  - `/ops`: Observability metrics, percentiles, runs, and granular spans (`endpoints/ops.py`).
  - `/memory`: Session history, context facts, and memory clearing (`endpoints/memory.py`).
  - `/setup`: System onboarding readiness checks (`endpoints/setup.py`).

---

## 5. Groq-Only LLM Integration

The LLM interface is strictly consolidated to the **Groq Cloud API** (`backend/app/llm/client.py`):
* **Provider:** `GroqLLMProvider` using the official `AsyncOpenAI` SDK configured to Groq's endpoint (`https://api.groq.com/openai/v1`).
* **No Cloud Multi-Tenancy:** Legacy fallback to Ollama, OpenAI, Anthropic, or Gemini has been permanently purged from production runtime.
* **Supported Production Models:**
  - `llama-3.3-70b-versatile`: Primary model for deep reasoning, multi-table planning, and executive narrative synthesis.
  - `openai/gpt-oss-120b`: High-capability alternative for complex analytical breakdowns.
  - `llama-3.1-8b-instant`: Ultra-fast model optimized for lightweight intent classification and simple query generation.
* **Resilience:** Bounded retries (max 2 attempts) with exponential backoff on `RateLimitError` (HTTP 429) and `APITimeoutError`.
* **Testing:** Deterministic `MockLLMProvider` isolated exclusively to offline unit test suites (`backend/tests/`).

---

## 6. Agentic Orchestration Architecture
*(Companion Diagram: Level 3 [`03_agentic_workflow_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/03_agentic_workflow_architecture.mmd))*

The autonomous decision-support system is driven by the **`AgenticSupervisor`** (`backend/app/orchestration/supervisor.py`):
1. **Question Understanding:** Extracts structured business entities (`StructuredQuestionRepresentation`) including target metrics, dimensions, temporal bounds, and literal filters (`entity_extractor.py`).
2. **Intent & Complexity Classification:** Classifies the request into primary intent (`DESCRIPTIVE`, `DIAGNOSTIC`, `PREDICTIVE`, `PRESCRIPTIVE`, `SQL_LOOKUP`) and complexity tier (`SIMPLE`, `MODERATE`, `COMPLEX`, `ADVANCED`) with confidence scoring (`intent_classifier.py`).
3. **Analytical Planning (DAG):** Generates an ordered task dependency graph specifying execution nodes and data requirements (`planner.py`).
4. **Specialist Delegation (`specialists.py`):**
   - **`DataRetrievalSpecialist`:** Discovers schema, generates read-only SQL, validates AST, and extracts DataFrames.
   - **`DiagnosticSpecialist`:** Performs variance decomposition, driver ranking, and statistical impact evaluations.
   - **`PredictiveSpecialist`:** Trains forecasting models, evaluates backtests, generates prediction intervals, and scores churn risk.
   - **`PrescriptiveSpecialist`:** Executes what-if simulations and constrained mathematical optimizations.
   - **`CriticSpecialist`:** Audits synthesized claims against computed numbers to block hallucinations.
5. **Executive Synthesis:** Compiles findings into a standardized briefing structured into **WHAT** happened, **WHY** it happened, **WHAT NEXT** to expect, and **SO WHAT** is the business impact.

---

## 7. The Seven Business Analytical Categories
*(Companion Diagram: Level 5 [`05_analytical_intelligence_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/05_analytical_intelligence_architecture.mmd))*

All analytical capabilities map directly to verified Python calculation modules:

| PRD Category | Implemented Algorithms & Techniques | Primary Engine Module |
| :--- | :--- | :--- |
| **1. Data Discovery** | Schema introspection, foreign-key relationship graph traversal, column profiling. | `schema/service.py`, `retrieval/hybrid.py` |
| **2. Descriptive Analytics** | SQL aggregation, Pandas vectorization, period-over-period delta ($\Delta\%$), trend extraction. | `analysis/descriptive_engine.py`, `descriptive.py` |
| **3. Diagnostic Analytics** | Variance decomposition, driver ranking, Median Absolute Deviation (MAD), Z-score, Isolation Forest. | `analysis/diagnostic_engine.py`, `diagnostic.py`, `anomalies.py` |
| **4. Impact Analytics** | Absolute and percentage delta, Student's t-test ($p$-value $<0.05$), 95% confidence intervals, dollar risk exposure. | `analysis/impact_engine.py` |
| **5. Predictive Analytics** | Holt-Winters Exponential Smoothing, ARIMA/SARIMAX, LightGBM, sliding-window backtesting, RFM churn risk scoring. | `analysis/predictive_engine.py`, `forecasting.py`, `churn_engine.py` |
| **6. Scenario Analytics** | Parameter perturbation, price/demand elasticity multipliers, baseline vs simulation comparative matrices. | `analysis/scenario_engine.py`, `scenarios.py` |
| **7. Prescriptive Analytics** | SciPy SLSQP constrained optimization, budget limits, operational bounds, trade-off matrices. | `analysis/prescriptive_engine.py`, `optimization.py` |

---

## 8. Hybrid RAG & Schema Grounding Pipeline
*(Companion Diagram: [`04_rag_schema_grounding_pipeline.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/04_rag_schema_grounding_pipeline.mmd))*

To prevent LLM hallucinations, schema context is assembled dynamically:
1. **Document Corpus:** Each table is converted into a structured document containing column names, data types, distinct sample values, and descriptions (`corpus.py`).
2. **Dense Vector Retrieval:** FastEmbed (`BAAI/bge-small-en-v1.5` ONNX) embeds table descriptions into **LanceDB** vector storage (`data/lancedb/<fingerprint>/`). Top 20 candidates retrieved by cosine similarity.
3. **Lexical Retrieval:** **Persistent BM25Okapi** index (`data/bm25/<fingerprint>/`) scores term overlap against query tokens. Top 20 candidates retrieved.
4. **Reciprocal Rank Fusion (RRF):** Fuses ranks using constant $k=60$:
   $$\text{RRF Score}(t) = \frac{1}{60 + \text{rank}_{\text{BM25}}(t)} + \frac{1}{60 + \text{rank}_{\text{Dense}}(t)}$$
   Selects the top $K=5$ initial tables.
5. **Foreign-Key Graph Expansion:** Traverses relational foreign keys from top-5 tables. Expands join path tables up to `max_expanded = 7` if tokens overlap with query.
6. **Fuzzy Value Linking:** Queries database distinct column values (`value_linker.py`) to ground natural language terms (e.g., `'SP'` $\rightarrow$ `'sao paulo'`) into exact SQL literal values.
7. **Semantic Layer:** Reconciles metric synonyms and dialect date functions (`semantics.py`).

---

## 9. Schema-Grounded SQL Pipeline & Safety Guardrails
*(Companion Diagram: [`04_rag_schema_grounding_pipeline.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/04_rag_schema_grounding_pipeline.mmd))*

Generated SQL traverses a multi-layered security gate before touching the database:
1. **Prompt Constraints:** Dialect-specific prompt enforcing read-only `SELECT` statements, forbidding column invention.
2. **SQL AST Validation (`sqlglot`):**
   - Disallows all mutation commands: `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `CREATE`, `TRUNCATE`.
   - Blocks dangerous system builtins: `ATTACH`, `LOAD_EXTENSION`, `xp_cmdshell`.
   - Rejects multi-statement queries (semicolon chaining) and comment tricks (`--`, `/*`).
3. **Bounded Repair Loop (`sql_repair.py`):** If a syntax or execution error occurs, feeds the exact database traceback back to Groq for bounded correction (capped at 2 retries).
4. **Safe SQL Execution (`sql_executor.py`):**
   - Timeout cap: 15 seconds.
   - Row limit cap: 5,000 rows.
   - Clean serialization into typed Pandas DataFrames.

---

## 10. Database Adapters & Connection Management
*(Companion Diagram: Level 6 [`06_database_onboarding_and_preparation.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/06_database_onboarding_and_preparation.mmd))*

The database layer (`backend/app/db/`) supports multiple relational engines via an adapter interface (`base.py`):
* **SQLite Adapter (`adapters/sqlite.py`):** Enforces `PRAGMA query_only = ON` and `PRAGMA busy_timeout = 5000`. Supports local files and uploaded databases.
* **PostgreSQL Adapter (`adapters/postgres.py`):** Sets `SET SESSION CHARACTERISTICS AS TRANSACTION READ ONLY` on pool checkout.
* **MySQL Adapter (`adapters/mysql.py`):** Sets `SET SESSION TRANSACTION READ ONLY`.
* **Database Connection Manager (`manager.py`):** Coordinates runtime database switching, state propagation, and connection lifecycle.

---

## 11. Asynchronous Schema Preparation Pipeline
*(Companion Diagram: Level 6 [`06_database_onboarding_and_preparation.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/06_database_onboarding_and_preparation.mmd))*

When a database is onboarded or switched, the **`SchemaJobManager`** (`backend/app/schema/job.py`) executes a 7-stage asynchronous preparation job in the background:
1. **Stage 1 (Connection Verification):** Validates connectivity, tests read-only enforcement.
2. **Stage 2 (Schema Discovery):** Introspects tables, views, primary keys, and foreign keys.
3. **Stage 3 (Table Profiling):** Calculates row cardinalities, distinct counts, null rates, and min/max ranges (`profiler.py`).
4. **Stage 4 (Semantic Metadata Construction):** Builds textual table documents and registers metrics.
5. **Stage 5 (Dense Vector Indexing):** Encodes table embeddings and indexes LanceDB vector tables.
6. **Stage 6 (Lexical BM25 Indexing):** Tokenizes corpus and persists the BM25Okapi index.
7. **Stage 7 (Preparation Verification):** Runs a verification retrieval query to confirm indexing integrity.
* **Fingerprint Isolation:** Indices are stored under `data/lancedb/<fingerprint>/` and `data/bm25/<fingerprint>/`. Database switching checks for pre-existing artifacts on disk and achieves sub-50ms warm-load readiness.

---

## 12. Conversational Context & Memory Service

The **`MemoryService`** (`backend/app/memory/service.py`) manages multi-turn conversational recall:
* **Session Persistence:** Backed by SQLite in `agent_app.sqlite` (`chat_sessions`, `chat_turns`, `memory_facts`).
* **Database Fingerprint Isolation:** Sessions are strictly keyed by `(session_id, db_fingerprint)` to prevent cross-warehouse context contamination.
* **Context Resolution:** Reconciles follow-up pronouns (e.g., *"What about in São Paulo?"* carries forward previous metrics like *revenue* and *quarterly filters*).

---

## 13. Security Architecture
*(Companion Diagram: Cross-Cutting [`09_security_observability_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/09_security_observability_architecture.mmd))*

The system enforces defense-in-depth across 4 boundaries:
1. **Credential Boundary:** API keys stored exclusively in `.env` (excluded from Git). Redacted in structured logs (`SensitiveDataFilter`). Client browser never receives LLM or database credentials.
2. **Database Boundary:** Physical read-only pragmas and transaction modes prevent data corruption or leakage.
3. **AST Guardrail Boundary:** `sqlglot` parser blocks injection attempts, mutations, multi-statements, and system routines.
4. **Agentic Boundary:** Prompt injection heuristic guards (`guardrails.py`) detect adversarial jailbreak attempts and return safe abstentions.

---

## 14. Observability & Telemetry Architecture
*(Companion Diagram: Cross-Cutting [`09_security_observability_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/09_security_observability_architecture.mmd))*

The system utilizes a dedicated operational database **`agent_app.sqlite`** (separate from LanceDB):
* **`ops_run_traces` Table:** Records run ID, session ID, query text, intent category, total monotonic latency, SQL query, row count, error classification, verification status, orchestrator type (`agentic_supervisor` vs `workflow_orchestrator`), Groq LLM model, token counts, and streaming timestamps.
* **`ops_stage_spans` Table:** Captures granular stage-level spans with monotonic start/end times and metadata.
* **Statistical Percentile Engine:** Computes exact non-parametric p50, p95, and p99 latencies, success rates, and error breakdowns via `GET /api/v1/ops/metrics`.

---

## 15. Performance Architecture & Latency Instrumentation

Stage-level latency is measured monotonically across 13 execution checkpoints:
1. Request Reception & Auth
2. Intent Classification & Entity Extraction
3. Hybrid Schema Retrieval
4. Groq Request Preparation
5. Groq Cloud Inference (LPUs)
6. SQL Generation
7. `sqlglot` AST Validation
8. Database Execution
9. Python Analytical Calculation
10. Specialist Orchestration Coordination
11. Critic & Evidence Verification
12. Final Answer Synthesis
13. Response Delivery / Stream Sentinels

* **Streaming Telemetry:** Tracks Time to First Event (TTFE, immediate progress indicator) and Time to First Output (TTFO, first meaningful token) to maintain responsive user feedback.

---

## 16. Deployment and Infrastructure Architecture
*(Companion Diagram: Level 7 [`07_deployment_and_infrastructure.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/07_deployment_and_infrastructure.mmd))*

The application topology is designed for high-concurrency local or containerized execution:
1. **Client Tier:** Modern web browsers executing the Next.js 14 single-page React client with client-side state caching and Plotly.js chart rendering.
2. **Application Tier:**
   - **Frontend Node.js Server:** Hosted on port 3001, providing static asset caching, server-side rendering, and API reverse proxying.
   - **Backend ASGI Server:** High-throughput Python 3.10+ runtime powered by Uvicorn on port 8001 hosting the FastAPI gateway, multi-agent orchestrator, deterministic analytical engines, and schema preparation workers.
3. **Storage Tier:** Isolated local filesystem storage volumes hosting `agent_app.sqlite` (traces and session memory), LanceDB vector tables, persistent BM25 inverted indexes, and metadata catalog cache snapshots.
4. **External Services Tier:** Ultra-fast Groq Cloud LPU clusters for accelerated open-weight model inference, alongside connected enterprise database clusters (SQLite, PostgreSQL, MySQL) queried under strict read-only constraints.

---

## 17. End-to-End Query Execution Sequence
*(Companion Diagram: Dynamic View [`08_end_to_end_execution_sequence.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/08_end_to_end_execution_sequence.mmd))*

The execution sequence diagram traces an entire conversational query turn:
1. Business user submits a natural language analytical inquiry.
2. Gateway assigns an active request trace ID and authenticates context.
3. Conversational memory retrieves preceding session turns and active database fingerprint.
4. Entity and intent engines parse metrics, dimensions, temporal boundaries, and classify intent.
5. Hybrid retriever executes parallel FastEmbed dense search and BM25 lexical search, applying Reciprocal Rank Fusion ($k=60$) and foreign key graph traversal.
6. Supervisor generates an analytical plan DAG and dispatches tasks to specialist agents.
7. Data Retrieval Specialist queries Groq Cloud LPUs for dialect-specific SQL.
8. Security AST validator parses syntax via `sqlglot`, verifying read-only enforcement before database execution.
9. Deterministic Python engines calculate statistical drivers, forecasts, what-if simulations, or impact metrics.
10. Evidence critic audits calculated numbers against narrative statements to prevent hallucinations.
11. Real-time Server-Sent Events (SSE) stream execution steppers, final executive management brief (WHAT, WHY, WHAT NEXT, SO WHAT), and responsive Plotly visualizations to the browser.

---

## 18. Actual Implementation Status

Refer to the companion verification matrix:
👉 [`docs/architecture/ARCHITECTURE_IMPLEMENTATION_VERIFICATION.md`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/ARCHITECTURE_IMPLEMENTATION_VERIFICATION.md)

* **Backend:** 100% of core components verified, tested, and active.
* **Frontend:** Next.js App Router architecture, AppShell, ChatInterface, ObservabilityDashboard, SchemaReadinessSection, and self-service connection setup are verified and functional.
* **LLM:** Groq Cloud API is the single verified production LLM provider.

---

## 19. Remaining Planned Enhancements

While core functionality is production-ready, the following architectural enhancements remain on the roadmap:
1. **Automated Continuous Pre-Warming:** Background daemon to pre-calculate LanceDB embeddings during off-peak hours for multi-gigabyte warehouse uploads.
2. **Fine-Grained Column Masking:** Policy-driven dynamic column-level PII masking for HIPAA/GDPR environments.
3. **Distributed Session Clustered Cache:** Migration from local SQLite session storage to a distributed cluster for multi-pod Kubernetes deployments.

---

### Complete Architecture Artifact Suite (`docs/architecture/`)
1. [`README.md`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/README.md) — Comprehensive Architecture Suite Guide & Diagram Index
2. Level 1: [`01_system_context.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/01_system_context.mmd)
3. Level 2: [`02_high_level_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_high_level_application_architecture.mmd)
4. Level 2 (UI): [`02_frontend_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_frontend_application_architecture.mmd)
5. Level 3: [`03_agentic_workflow_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/03_agentic_workflow_architecture.mmd)
6. Level 4: [`04_rag_schema_grounding_pipeline.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/04_rag_schema_grounding_pipeline.mmd)
7. Level 5: [`05_analytical_intelligence_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/05_analytical_intelligence_architecture.mmd)
8. Level 6: [`06_database_onboarding_and_preparation.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/06_database_onboarding_and_preparation.mmd)
9. Level 7: [`07_deployment_and_infrastructure.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/07_deployment_and_infrastructure.mmd)
10. Dynamic: [`08_end_to_end_execution_sequence.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/08_end_to_end_execution_sequence.mmd)
11. Cross-Cutting: [`09_security_observability_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/09_security_observability_architecture.mmd)
12. Verification: [`ARCHITECTURE_IMPLEMENTATION_VERIFICATION.md`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/ARCHITECTURE_IMPLEMENTATION_VERIFICATION.md)

