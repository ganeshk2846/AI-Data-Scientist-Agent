# Prompt for AI Coding Tool --- AI-Powered Data Scientist Agent for Business Intelligence

## Role and operating rules

You are the lead software architect, senior full-stack engineer, data
engineer, ML engineer, and QA engineer responsible for building this
project from an empty repository to a working, tested application.

Build an **AI-Powered Data Scientist Agent for Business Intelligence (AI
for BI)** using the supplied SQLite dataset
`ecommerce.sqlite`. The application must let a user ask
business questions in natural language, retrieve and use the real
database schema, generate and validate SQL, execute safe read-only
queries, analyze results, produce charts, explain findings, and---when
evidence supports it---perform diagnostic, predictive, and prescriptive
analysis.

You must implement the project **phase by phase**. Do not attempt to
generate the whole system in one pass. Finish the current phase, run its
checks, update `DEVELOPMENT_HISTORY.md`, and only then begin the next
phase.

### Mandatory working rules

1.  **Inspect before changing.** Begin by inspecting the repository,
    runtime, available files, and the provided
    `ecommerce.sqlite` database. Do not assume the schema,
    table names, columns, row counts, date ranges, or data quality.
    Discover and document them.
2.  **Respect the supplied database.** Treat
    `ecommerce.sqlite` as the project's source dataset. Never
    silently replace it with a downloaded dataset, synthetic data, or a
    differently named database. If it is not present, report the exact
    expected path and create a clear setup instruction; do not fabricate
    results.
3.  **Phase gate.** Work on only one phase at a time. At the end of each
    phase, run relevant tests/checks, record the outcome, list known
    issues, and update `DEVELOPMENT_HISTORY.md`. Do not claim a test
    passed unless it was actually run.
4.  **History is mandatory.** Create and maintain a root-level
    `DEVELOPMENT_HISTORY.md`. Update it immediately after every phase,
    recording implementation, files changed, commands/tests run and
    their actual outcomes, decisions, limitations, and the next phase.
    Preserve earlier entries; append a dated entry rather than
    overwriting history.
5.  **Keep the project runnable.** After each phase, leave the
    repository in a coherent state. Avoid large untested changes across
    multiple phases. Prefer small, reviewable increments.
6.  **No fake functionality.** Do not use placeholder responses that
    pretend to be database answers, fabricated metrics, mock charts
    presented as real, or hard-coded dataset-specific assumptions.
    Clearly label any demo-only UI.
7.  **Schema-grounded SQL.** Generate SQL only from tables and columns
    retrieved from the actual connected database. Never invent
    identifiers. Validate SQL before execution.
8.  **Safe database access.** The source SQLite database is read-only
    for the application. Allow only validated read-only queries; block
    writes, DDL, ATTACH/DETACH, extension loading, unsafe pragmas, and
    multiple-statement execution. Apply query timeouts/limits where
    supported.
9.  **Bounded recovery.** Permit at most two automatic SQL repair
    attempts after a validation or execution error. Each retry must use
    the actual error and retrieved schema; then stop and explain the
    limitation or ask a clarification question.
10. **Truthfulness and evidence.** Every factual numeric/business claim
    in the final answer must be traceable to query output or a
    documented analysis result. If the data cannot answer a question,
    say so. Do not present correlation as causation or predictions as
    certainty.
11. **No hidden chain-of-thought exposure.** Show concise progress
    states, actions, tools used, query summaries, and evidence---not
    private internal reasoning. Never expose secrets, raw credentials,
    or sensitive configuration.
12. **Use configuration and environment variables** for API keys and
    application settings. Add `.env.example`, and ensure `.env`, database
    copies, caches, logs with sensitive content, and generated secrets
    are excluded from version control.
13. **Do not over-engineer before the MVP works.** Build a reliable
    vertical slice first, then add retrieval, advanced analysis, memory,
    and production hardening in later phases.
14. **Ask only blocking questions.** Use sensible documented defaults
    for non-blocking choices. If a decision would risk data loss,
    security, cost, or a major architectural fork, stop and ask before
    proceeding.
15. **Explain commands.** Keep a `README.md` with setup, run, test,
    configuration, architecture, dataset expectations, and
    troubleshooting instructions.

## Product goal and user workflow

The intended workflow is:

1.  User opens the application and sees connection/readiness status.
2.  The app loads the supplied SQLite database in read-only mode.
3.  An onboarding/preparation process inspects tables, columns, types,
    primary/foreign keys where available, row counts, null rates, sample
    values, date columns, and likely relationships. Do not expose
    unnecessary sensitive row samples.
4.  The app creates a searchable schema catalogue and records the
    preparation status.
5.  User asks a natural-language business question.
6.  A Router classifies intent and difficulty.
7.  A Grounder retrieves relevant schema elements and business
    definitions, with confidence scoring.
8.  If key details are missing or the schema evidence is weak, a
    Clarification Agent asks a focused question or the Answerability
    Gate abstains.
9.  A Planner creates a typed, inspectable plan (for example: SQL
    retrieval, aggregation, comparison, trend, anomaly, forecast, driver
    analysis, or recommendation).
10. The Executor runs validated read-only SQL and deterministic Python
    analysis tools in a controlled workflow.
11. The Verifier checks execution status, result quality, empty results,
    arithmetic, and claim-to-evidence consistency.
12. The Visualization Agent creates a chart specification from actual
    result data; the UI renders the chart or provides a useful
    table/text fallback.
13. The Composer returns a clear answer with key findings, assumptions,
    evidence, chart/table, limitations, and suggested follow-up
    questions.
14. The run is logged with trace IDs, status, latency, and safe
    diagnostic metadata. Relevant conversation context may be saved
    according to the memory policy.

## Mandatory technology stack and development constraints

Use this stack as the default. Do not silently substitute competing
frameworks. If repository inspection finds a concrete incompatibility,
document the evidence and propose the smallest change before implementing it.

- **Backend language/API:** Python and FastAPI.
- **Backend contracts:** Pydantic v2; export JSON Schema for shared contracts.
- **Frontend:** Next.js App Router, React, TypeScript, Tailwind CSS, shadcn/ui, and TanStack Query.
- **Frontend contract validation:** Zod for event and chart payloads.
- **Visualization:** Plotly.js; render only validated chart specifications derived from actual query/analysis results. Always provide a table/text fallback.
- **Streaming:** Server-Sent Events (SSE), with typed event envelopes and persisted run events so reconnect/resume behavior can be tested.
- **Workflow orchestration:** LangGraph with checkpointed state. Do not replace it with a custom state machine without documenting a concrete compatibility reason and obtaining approval.
- **Business data:** the supplied `ecommerce.sqlite`, opened read-only. Never modify, migrate, regenerate, or silently replace it.
- **Application/agent state:** a separate writable SQLite database for local development and tests. Keep repositories behind SQLAlchemy. Use Alembic only for the agent-owned database, never the business dataset.
- **SQL safety:** `sqlglot` for parsing and validation; allowlisted identifiers; parameterized values; read-only access; query/result limits; and SQLite-compatible query-plan checks.
- **Schema retrieval:** BM25 lexical retrieval plus embedding retrieval; combine rankings with reciprocal-rank fusion (RRF). Keep embedding/vector access behind an interface and provide a local implementation and a BM25 fallback. Select and document the actual default embedding model and local index implementation; do not invent that these are already configured.
- **Core analysis:** pandas, statsmodels, scikit-learn, SciPy, and Prophet where the corresponding feature is implemented. Use deterministic calculations and simple baselines first; numerical results must be independently verified from LLM-generated prose.
- **Optional advanced analysis (not assumed installed and not mandatory on every question):** Isolation Forest + STL-ESD + PELT for anomaly/change detection; CatBoost + SHAP for predictive driver analysis; Double Machine Learning (Double ML) only for defensible treatment-effect estimation; AutoARIMA and LightGBM as forecasting candidates. Likely optional packages include `ruptures` (PELT), `catboost`, `shap`, `doubleml`, `pmdarima` (AutoARIMA), and `lightgbm`. Inspect the environment and dataset first; add only the dependencies needed for a phase, pin/document versions, and preserve a tested simpler fallback.
- **Testing:** pytest for backend tests, a documented frontend test framework, and end-to-end tests for the core question-to-answer journey.
- **Configuration:** typed application settings and environment variables; maintain `.env.example` with placeholders only. The app must start without LLM credentials and clearly report which LLM-dependent features are unavailable.
- **LLM integration:** provider-agnostic wrapper with configured model names, timeouts, bounded retries, and token/cost limits. Do not hard-code provider-specific behavior into agent logic.

**Explicit non-use decision:** Redis is not part of the current development stack. Do not install, configure, import, require, or assume Redis or Redis-backed queues/caches/checkpointers. Use the application-owned SQLite store and LangGraph's supported local checkpoint persistence for this development version. Do not add Docker, Kubernetes, cloud queues, hosted vector services, or production deployment configuration to this coding task.

Keep the frontend and backend modular. Preserve the existing repository layout where practical; document any necessary structural change before making it.

## Advanced-model implementation and anti-hallucination rules

The following are candidate methods, not claims that the repository already contains them and not a requirement to run every method for every request:

- **Anomalies/change points:** compare a robust-z-score baseline with STL-ESD for seasonal series; use Isolation Forest only with appropriate multivariate features; use PELT only for ordered data with enough observations. Check data quality before interpreting anomalies.
- **Drivers:** deterministic variance/mix decomposition is the first baseline. CatBoost may improve nonlinear prediction/ranking and SHAP may explain that model's predictions; do not describe SHAP values or observational associations as causal proof. Double ML is allowed only when treatment, outcome, confounders, sample sufficiency and causal identification assumptions are documented; otherwise provide association-level results and caveats.
- **Forecasting:** benchmark AutoARIMA and LightGBM against seasonal-naive/ETS (and Prophet where appropriate) using rolling-origin holdouts, horizon-specific errors and interval coverage where available. Do not assume one model is best before evaluation.
- **Evidence and dependencies:** inspect the actual repository, installed packages, schema, data volume and time coverage before selecting a method. Do not claim a package is installed, a model is implemented, or performance improved without command/test/benchmark evidence. Add optional dependencies only for a justified feature; retain fallback behavior for missing packages, insufficient data, timeouts and poor validation scores.
- **Scope control:** implement incrementally by phase. Do not install or wire all optional models at once merely because they are listed. Record model choice, baseline, dataset split, metrics, runtime and limitations in `DEVELOPMENT_HISTORY.md` and the evaluation report.

## Required architectural principles

Implement the pipeline:

**Retrieve → Constrain → Plan → Generate → Validate → Execute → Verify →
Analyze → Visualize → Explain**

Core services/components should have clear responsibilities:

-   **Router Agent:** classify request intent and complexity, and select
    the appropriate workflow.
-   **Context Resolver / Memory Service:** load relevant conversation
    context and persist useful session state without treating memory as
    a source of truth for database facts.
-   **Schema Grounder:** retrieve real table/column definitions,
    relationships, data profiles, and optional business definitions.
-   **Answerability Gate:** decide whether the evidence is sufficient;
    request clarification or abstain when appropriate.
-   **Clarification Agent:** ask the minimum useful question when
    ambiguity materially affects correctness.
-   **Planner Agent:** produce a structured plan with typed steps and
    explicit tool inputs/outputs.
-   **Executor:** run a controlled DAG/workflow using approved tools; no
    arbitrary shell execution or unrestricted code execution from model
    output.
-   **SQL Generator:** generate SQL only using retrieved schema
    identifiers.
-   **SQL Validator / Guardrail:** parse SQL, enforce read-only policy,
    verify identifiers and limits, and reject disallowed operations
    before execution.
-   **Repair loop:** maximum two attempts, bounded and observable.
-   **Deterministic Analysis Tools:** calculate summaries, trends,
    segment comparisons, contribution/variance, outliers, statistical
    tests, forecasts, and what-if calculations only when appropriate and
    supported by the data.
-   **Verifier / Faithfulness Checker:** compare answer claims with
    actual results and reject unsupported claims.
-   **Visualization Agent:** choose an appropriate chart from result
    shape and task; emit a validated chart specification.
-   **Composer:** return a coherent business-oriented answer with
    evidence and caveats.
-   **Observability/Evaluation:** record run IDs, phase statuses, tool
    calls, failures, latency, token/cost metadata when available, and
    evaluation metrics.

Do not implement agents as separate services solely for appearance. They
may initially be typed modules/classes in one backend, provided the
boundaries and contracts are explicit and testable.

## Phase-by-phase implementation plan

### Phase 0 --- Repository and dataset reconnaissance

**Objective:** Understand the starting environment and actual SQLite
dataset before choosing detailed implementation decisions.

Tasks: - Inspect repository files, package managers, installed runtimes,
and existing code. - Find `ecommerce.sqlite`. If the file is
elsewhere, inspect likely project paths; do not search unrelated private
locations. - Verify the database can be opened in read-only mode. -
Inventory tables/views, columns, SQLite types, row counts,
primary/foreign keys, indexes, and available schema SQL. - Profile null
counts, distinct counts, likely date fields, numeric ranges, duplicate
patterns, and small safe samples where useful. - Identify likely
e-commerce entities and relationships only from actual evidence; do not
assume table names. - Record data limitations and whether the database
is suitable for trends, forecasting, segmentation, or other analyses. -
Propose final repository layout and note any changes from the baseline
stack.

Deliverables: - `DEVELOPMENT_HISTORY.md` created with a Phase 0 entry. -
`docs/DATASET_PROFILE.md` with verified dataset inventory and quality
observations. - Initial `README.md` or setup notes. - No fabricated
dataset facts.

Acceptance checks: - The database opens read-only. - The profile is
generated from the actual file. - Schema/table/column names and counts
are evidenced by executed inspection commands. - Missing dataset or
access issues are clearly reported.

**Stop after Phase 0, update the history, and report results before
starting Phase 1.**

### Phase 1 --- Project foundation and developer experience

**Objective:** Establish a clean, runnable, testable application
skeleton.

Tasks: - Create frontend/backend structure, dependency manifests, typed
configuration, formatting/linting, and test setup. - Add `.gitignore`,
`.env.example`, README setup steps, and safe logging defaults. - Add
backend health/readiness endpoints and a frontend shell with a clear
loading/error state. - Add structured error models, request IDs, and
consistent API response conventions. - Add startup checks for database
path, read-only access, and required configuration. - Keep LLM provider
optional at this stage. - Add a minimal local development workflow and
commands.

Deliverables: - Runnable frontend and backend. - Health/readiness UI and
endpoints. - Tests for configuration and health endpoints. -
`DEVELOPMENT_HISTORY.md` Phase 1 entry.

Acceptance checks: - Documented commands start both apps. - Lint/type
checks and initial tests run successfully, or failures are recorded
accurately. - No secrets or source database are accidentally committed.

### Phase 2 --- Read-only database connection and schema preparation

**Objective:** Build the trustworthy data foundation.

Tasks: - Implement a database connection manager for
`ecommerce.sqlite` using a read-only connection/URI where
supported. - Add robust path resolution and useful error messages. -
Implement schema introspection and profile generation. - Persist
generated catalogue/profile data in a separate application metadata
store or generated local artefacts; never mutate the source SQLite
database. - Represent tables, columns, data types, primary/foreign keys,
indexes, date candidates, numeric candidates, and profile summaries in
typed models. - Add an asynchronous preparation job with states such as
`pending`, `running`, `succeeded`, `failed`, and progress events. - Make
preparation idempotent and record a source fingerprint or modification
metadata so stale indexes can be detected. - Do not send full raw tables
to an LLM; provide only the minimum relevant schema and safe profile
context. - Display table/schema readiness and preparation errors in the
UI.

Deliverables: - Database service, schema catalogue, profiling utilities,
preparation job, and readiness UI. - Unit/integration tests using the
actual dataset plus small temporary test databases. - Updated dataset
and architecture documentation.

Acceptance checks: - Application can list the real tables and columns. -
The source database remains unchanged. - Preparation can be rerun
safely. - Missing/invalid paths and malformed schema cases are handled
clearly.

### Phase 3 --- Natural-language question API and first reliable vertical slice

**Objective:** Support a complete but narrow question-to-answer workflow
before adding advanced agents.

Tasks: - Build chat/session APIs and the first usable chat UI. -
Implement a provider-agnostic LLM interface with typed request/response
contracts and timeout/error handling. - Add a simple Router for
descriptive, comparative, trend, diagnostic, predictive, and
prescriptive intent labels; confidence must be recorded. - Retrieve the
actual relevant schema for each question. - Generate a single SQL
candidate using only the retrieved schema. - Validate SQL, execute
read-only, return result metadata and rows safely, and produce a concise
answer grounded in results. - Show user-visible progress states such as
`understanding_question`, `retrieving_schema`, `validating_query`,
`running_query`, `verifying_results`, and `composing_answer`. - Include
trace/run IDs and useful error messages. - When LLM credentials are
missing, show a clear setup message rather than faking an answer.

Deliverables: - End-to-end question → schema → SQL → validation →
execution → answer workflow. - SQL display/inspection option and results
table. - Tests for success, missing schema, provider failure, SQL
failure, and empty result cases.

Acceptance checks: - At least one natural-language question can be
answered against the actual SQLite data when the provider is
configured. - SQL identifiers are checked against the real schema. - A
database error never becomes a fabricated successful answer.

### Phase 4 --- Multi-agent workflow, planning, clarification, and bounded repair

**Objective:** Make the workflow explicit, inspectable, and robust.

Tasks: - Implement clear contracts for the four first-class agents:
Router, Planner, Clarification, and Visualization. - Add Context
Resolver, Grounder, Answerability Gate, Executor, Verifier, and Composer
as explicit modules with typed inputs/outputs. - Implement a typed
execution plan / DAG with step status, dependencies, tool arguments,
outputs, and failure handling. - Use a workflow/state mechanism
(LangGraph or a simpler explicit state machine if it meets requirements)
with checkpoints for recoverability. - Ask clarification when different
interpretations materially change the result. - Add confidence
thresholds and safe abstention when schema evidence is weak or data does
not support the question. - Add a maximum of two SQL repair retries;
validate each repaired query again from scratch. - Enforce query
timeouts, row limits, and result-size limits. Do not rely only on a
generated `LIMIT` clause for safety. - Do not stream private
chain-of-thought. Stream only short status updates and safe explanations
of completed actions.

Deliverables: - Typed agent contracts and workflow orchestration. -
Clarification UI and safe abstention path. - Workflow unit/integration
tests and failure-path tests.

Acceptance checks: - Workflow steps and failures are observable. -
Ambiguous requests can trigger a clarification question. - Repairs never
bypass validation and stop after two attempts. - Unsupported questions
are refused or narrowed instead of guessed.

### Phase 5 --- Hybrid schema retrieval and business semantics

**Objective:** Improve retrieval quality beyond putting the entire
schema in the prompt.

Tasks: - Build a schema-document corpus from actual DDL, table/column
descriptions where available, foreign-key links, data profiles, and
user-supplied business definitions. - Implement lexical retrieval (for
example BM25) plus embedding retrieval behind replaceable interfaces;
combine results using a documented ranking/fusion method such as
reciprocal-rank fusion. - Add table/column relevance scoring and
foreign-key graph expansion to retrieve join context. - Add value
linking for natural-language values to actual database values. Start
with safe, low-cardinality value indexes; use bounded, parameterized
lookups for high-cardinality values. - Do not index or expose sensitive
sample values unnecessarily. - Add optional semantic definitions for
business metrics and synonyms. Distinguish verified definitions from
inferred suggestions. - Add retrieval confidence, source references, and
debug views for selected tables/columns. - Add caching only with clear
invalidation when the schema or catalogue fingerprint changes. - Do not add a vector database for the first functional vertical slice. Keep vector retrieval behind an interface and use the selected local index plus the BM25 fallback.

Deliverables: - Hybrid schema retriever, value linker,
semantic-definition model, retrieval evaluation dataset, and
diagnostics. - Tests for similarly named tables/columns, join-path
retrieval, value linking, and unknown terms.

Acceptance checks: - SQL generation receives only the selected,
retrieved schema context and required join paths. - Retrieval results
can be inspected and scored. - Unknown schema identifiers are rejected.

### Phase 6 --- Reliable analysis tools: descriptive, diagnostic, predictive, and prescriptive

**Objective:** Provide real data-scientist capabilities without asking
the LLM to invent calculations.

Tasks: - Implement deterministic tools for descriptive summaries,
aggregations, period-over-period comparisons, trends, cohort/segment
comparisons, distribution/outlier checks, and contribution analysis when
data supports them. - Add diagnostic/driver analysis with clearly stated
method, candidate drivers, sample sizes, uncertainty, and limits. Do not
claim causal proof from observational correlation. - Add forecasting
only when valid time-series data and sufficient history exist. Use
appropriate baselines first, time-aware validation, error metrics, and
forecast intervals where available. - Add what-if/scenario analysis with
explicit assumptions and sensitivity checks. - Add prescriptive
optimization only when a clear objective, decision variables,
constraints, and valid input data exist; otherwise explain what inputs
are missing. - Keep deterministic computation separate from LLM
narrative. - Do not automatically train a churn or other predictive
model unless the actual dataset has a defensible target and enough
suitable features/records. Detect feasibility and document
limitations. - Return typed analysis artefacts with provenance,
parameters, data window, and metrics.

Deliverables: - Tool registry and schemas for analysis tools. - Tests
for calculations, edge cases, missing data, small sample sizes, and
time-based splits. - Documentation for methods and when they must
abstain.

Acceptance checks: - Calculations are reproducible. -
Forecasts/diagnostics include limitations and evaluation where
applicable. - No unsupported prediction or causal claim is presented as
fact.

### Phase 7 --- Visualization and business-oriented answer composition

**Objective:** Turn validated data and analysis into clear business
communication.

Tasks: - Implement the Visualization Agent with a typed chart
specification and a strict allowlist of chart types, encodings, fields,
and aggregation assumptions. - Choose charts based on result shape and
question: line for time trends, bar for category comparisons, scatter
for relationships, histogram/box plot for distributions, and table for
exact values or unsuitable chart cases. - Render charts from actual
validated query/analysis results using Plotly.js or the chosen
library. - Validate chart specs; reject unknown columns, invalid series,
malformed values, and unsafe HTML/script content. - Provide a useful
fallback to table/text if chart rendering fails or data is unsuitable. -
Composer output should contain: direct answer, key findings, supporting
evidence, chart/table, assumptions, data coverage, caveats, and
suggested next questions. - Link every major numeric claim to
result/analysis evidence internally and retain trace IDs for
debugging. - Clearly label forecasted or estimated values.

Deliverables: - Chart specification schema, renderer, result table,
business answer component, and tests. - Responsive UI with loading,
empty, error, and unsupported-chart states.

Acceptance checks: - Charts use only actual returned data. - Every
displayed metric has a traceable source. - UI remains useful when chart
rendering fails.

### Phase 8 --- Shared memory, sessions, and reusable knowledge

**Objective:** Preserve useful context without letting memory override
database evidence.

Tasks: - Implement a central Memory Service used through shared
interfaces, not separate ad hoc memory logic in each agent. - Separate
memory categories: conversation/session history, resolved user
constraints, temporary working state, references to previous analysis
artefacts, user-approved preferences, and reusable successful
question/SQL examples. - Treat the live database and current query
results as the source of truth. Memory is contextual assistance, never
proof of current facts. - Define retrieval rules, precedence,
expiry/retention, per-user/session isolation, and deletion behavior. -
Store structured session data in a suitable relational store. Keep the
source e-commerce database read-only and separate from application
metadata. - Add vector retrieval only if needed for semantic
memories/examples, behind an interface with a clear local
configuration. - Avoid storing raw secrets, credentials, or unnecessary
PII. Provide a way to clear a session and document retention. - Add
tests for isolation, expiry, deletion, stale context, and preference
precedence.

Deliverables: - Memory Service, persistence adapters, retrieval
contracts, retention/deletion logic, and tests. - Documentation of what
is stored and why.

Acceptance checks: - A follow-up question can reuse relevant session
context. - Stale memory cannot override fresh database results. -
Session clearing/deletion behaves as documented.

### Phase 9 --- Security, observability, evaluation, and performance

**Objective:** Measure reliability and prepare for real use.

Tasks: - Add structured traces for each run, agent/tool step, SQL
validation result, retry, execution time, failure class, and answer
verification status. - Redact secrets and avoid logging unnecessary raw
data. - Add configurable request, query, row, memory, token, and cost
budgets. - Add query cost/safety checks suitable for SQLite; document
database-specific differences rather than pretending SQLite supports all
warehouse features. - Add prompt-injection defenses for user questions
and database text; treat schema descriptions and cell values as data,
never as instructions. - Add appropriate local request safeguards and session isolation. Do not implement public-service deployment requirements in this development phase. - Build a reproducible evaluation harness and a small gold
set of questions grounded in the actual dataset. - Compare against a
clearly defined naive baseline (for example, direct LLM-to-SQL using the
same database and comparable model settings). - Track metrics such as
schema validity rate, execution success, execution/result accuracy on
gold cases, hallucinated-identifier rate, clarification/abstention
quality, answer faithfulness, chart validity, p50/p95 latency, and
estimated cost where available. - Separate functional tests, security
tests, regression tests, and evaluation metrics. - Never fabricate
benchmark scores; report exact sample size, methodology, environment,
and limitations.

Deliverables: - Observability dashboard or run-inspection page,
evaluation script/report, security tests, and performance notes. -
`docs/EVALUATION.md` documenting metric definitions and measured
results.

Acceptance checks: - Tests verify write queries and invalid identifiers
are blocked. - Evaluation can be rerun and results are reproducible. -
Performance claims are backed by recorded measurements.

### Phase 10 --- End-to-end validation and final documentation

**Objective:** Deliver a maintainable application that another developer
can run.

Tasks: - Complete end-to-end tests for onboarding, database preparation,
asking questions, SQL validation/execution, clarification,
visualization, analysis, error recovery, and session follow-ups. - Test
with the actual `ecommerce.sqlite` file; include instructions
for placing it locally without committing it if its license/privacy
status is unknown. - Test no API key, invalid API key, missing database,
empty result, malformed LLM output, timeout, SQL syntax error, blocked
SQL, chart failure, and insufficient data for forecasting. - Add
startup/shutdown behavior, clear logs, accessibility basics, responsive
UI, and sensible empty/error states. - Review dependency security and
remove dead code, unused packages, debug secrets, and misleading mock
features. - Update README, architecture docs, API docs, dataset profile,
troubleshooting, evaluation report, and environment configuration. -
Ensure `DEVELOPMENT_HISTORY.md` accurately records every completed phase
and outstanding issue. - Provide final run/test commands and a clear
list of limitations and next steps.

Deliverables: - Complete working application and documentation. - Final
test/evaluation report. - Updated `DEVELOPMENT_HISTORY.md` with a final
status summary.

Acceptance checks: - The developer can follow the README to configure and run the application locally. - The app works with the provided database and
configured LLM provider. - No known blocker is hidden; all unimplemented
features are clearly marked.

## Mandatory `DEVELOPMENT_HISTORY.md` format

Create this file in the repository root in Phase 0. Preserve all
existing history if the file already exists. After each phase, append an
entry using this template:

``` markdown
## Phase N — Phase title
- **Date/time:**
- **Status:** Complete / Partial / Blocked
- **Objective:**
- **Implemented:**
  - ...
- **Files created/modified:**
  - ...
- **Commands executed:**
  - `command` — actual outcome
- **Tests/checks:** Passed / Failed / Not run, with exact summary
- **Dataset/schema observations:** Only when relevant; facts must come from actual inspection
- **Decisions and rationale:**
- **Known issues / limitations:**
- **Security/data-safety notes:**
- **Next phase:**
```

At the top of the file, maintain a compact project status table with
each phase, status, completion date, and link to relevant docs if
available. Update the table when a phase changes status, but do not
delete detailed earlier entries. Mark work as `Partial` or `Blocked`
honestly. Never write "complete" just because code was generated.

## Required repository documentation

At minimum, maintain: - `README.md` --- setup, configuration, run, test,
and troubleshooting. - `DEVELOPMENT_HISTORY.md` --- chronological
phase-by-phase implementation log. - `docs/DATASET_PROFILE.md` ---
verified database schema and data-quality profile. -
`docs/ARCHITECTURE.md` --- actual implemented architecture, not only the
intended design. - `docs/EVALUATION.md` --- metric definitions,
test/evaluation setup, and measured results. - `.env.example` ---
variable names and safe example values only.

Keep documentation aligned with the code. If the design changes, record
why in `DEVELOPMENT_HISTORY.md` and update the architecture document.

## Development scope exclusions

This task is local application development and testing, not deployment.
Do not create deployment manifests, Dockerfiles, Docker Compose files,
Kubernetes configuration, cloud hosting instructions, public URLs,
Redis services, managed queues, or production infrastructure. Do not add Redis
as a dependency for any purpose. Do not claim the application is deployed.
Keep local setup/run/test instructions in README.md and document any
future infrastructure idea as out of scope rather than implementing it.

## How to operate in the coding tool

At the start: 1. State briefly what you inspected and what is present.
2. Check whether `ecommerce.sqlite` is accessible. 3. Read
existing instructions and history before changing files. 4.
Create/update Phase 0 outputs only.

At the end of every phase: 1. Run the phase's relevant commands and
tests. 2. Inspect the diff and check for accidental data or secret
changes. 3. Update `DEVELOPMENT_HISTORY.md` with actual results. 4.
Summarize what was completed, what was tested, what remains, and the
exact next phase. 5. **Stop and wait for the user's approval before
starting the next phase.**

If the coding tool has a plan/task feature, create one task per phase
and mark tasks only according to actual completion. If context limits
require resuming in a new session, read `DEVELOPMENT_HISTORY.md`,
`README.md`, and the current code before continuing. Resume from the
first incomplete phase; do not repeat completed work unless a failed
check requires it.

## Definition of success

The project is successful when a user can connect to and prepare the
supplied SQLite dataset, ask natural-language business questions,
receive schema-grounded and validated answers, inspect the supporting
results, view appropriate data-driven visualizations, request supported
diagnostic/predictive/prescriptive analyses, get clarification or an
honest refusal when evidence is insufficient, and trace what the system
did through run logs and `DEVELOPMENT_HISTORY.md`.

**Begin with Phase 0 only. Inspect first; do not jump ahead or implement
all phases in one response.**