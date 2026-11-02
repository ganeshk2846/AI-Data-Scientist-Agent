# Frontend-to-Backend Integration Map & API Reference
**AI for BI — Data Scientist Agent**
*Authoritative API Integration Specification & Data Contracts*

---

## 1. Overview & Communication Architecture

The frontend communicates with the FastAPI backend over HTTP/1.1 and Server-Sent Events (SSE).

### 1.1 Base URL & Environment Configuration
- **Frontend API Base Definition:** `frontend/src/lib/api.ts` (Line 28):
  ```ts
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
  ```
- **Next.js Proxy Rewrite Configuration:** `frontend/next.config.mjs` (Lines 6–13):
  ```js
  async rewrites() {
    return [
      {
        source: '/api/backend/:path*',
        destination: `http://localhost:${backendPort}/api/v1/:path*`,
      },
    ];
  }
  ```
- **Architectural Discrepancy Note:** The frontend currently makes direct cross-origin calls to `http://localhost:8001` via `API_BASE_URL` rather than routing through the `/api/backend/*` proxy. In development, this succeeds because FastAPI includes `CORSMiddleware` with `allow_origins=settings.CORS_ORIGINS` and regex `r"^http://(localhost|127\.0\.0\.1)(:[0-9]+)?$"`.

### 1.2 Common API Envelope (`APIResponse[T]`)
Every JSON response from the backend adheres strictly to the typed Pydantic envelope defined in `backend/app/core/models.py` and validated on the client with Zod in `frontend/src/types/api.ts`:
```json
{
  "success": true,
  "data": { ... },
  "error": null,
  "request_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
}
```
When `success === false`, `data` is null and `error` contains:
```json
{
  "code": "RESOURCE_NOT_FOUND",
  "message": "Table 'non_existent_table' was not found in the catalog.",
  "details": { "available_tables": ["orders", "customers", "..."] },
  "timestamp": "2026-11-02T05:20:00Z"
}
```

### 1.3 Distributed Tracing Middleware
Every request triggers `RequestIdMiddleware` (`backend/app/main.py`), which propagates:
- `X-Request-ID`: Client-supplied or newly generated UUID.
- `X-Process-Time-Ms`: Server execution duration in milliseconds.

---

## 2. Comprehensive API Operation Catalog

The table below catalogs every API operation across both active UI features and declared client abstractions.

| # | Feature / Page | Trigger Event | Frontend Function | Method | Endpoint | Query / Path Params | Request Body | Backend Handler & File | Business Logic / Data Access | Response Type / Data Payload | Client Parsing & State Impact | Failure & Fallback Handling |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **1** | System Shell & Header | App mount & 15s interval | `fetchReadiness` | `GET` | `/api/v1/ready` | None | None | `get_readiness` (`health.py:31`) | `check_database_readiness()`, stat cache, LLM provider check | `ReadinessStatus` (`ready`, `database`, `llm`, `app_store_ready`) | Validated via `ReadinessResponseSchema`; updates Header status dot and `HealthReadinessCard` | Status code 503 if not ready; UI displays offline warning card with command instruction |
| **2** | Schema Explorer | Tab switch & 15s interval | `fetchSchemaStatus` | `GET` | `/api/v1/schema/status` | None | None | `get_schema_status` (`schema.py:39`) | Inspects `job_manager.get_latest_job()`, reads cached catalog | `SchemaStatus` (`is_prepared`, `latest_job`, `catalog_summary`) | Validated via `SchemaStatusResponseSchema`; adjusts poll interval (1.5s vs 15s) | Throws error; card displays "Unprepared" |
| **3** | Schema Explorer | Click "Run Preparation" or "Force Refresh" | `triggerSchemaPreparation` | `POST` | `/api/v1/schema/prepare` | `force: boolean` (query) | None | `prepare_schema` (`schema.py:16`) | Spawns background worker `start_preparation_job()`; introspects SQLite PRAGMAs | `PreparationJobState` (`job_id`, `status`, `progress_percent`, `message`) | Validated via `PreparationJobResponseSchema`; invalidates `schemaStatus` & `schemaTables` | Button disabled with spinner; error toast/message on network error |
| **4** | Schema Explorer | Table list mount | `fetchTables` | `GET` | `/api/v1/schema/tables` | None | None | `list_tables` (`schema.py:90`) | Retrieves cached catalog or profiles synchronously; sorts table summaries | `TableSummary[]` (`name`, `row_count`, `column_count`, `primary_keys`) | Validated via `TableListResponseSchema`; populates left-pane table selector | Displays loading text; error message if catalog missing |
| **5** | Schema Explorer | User selects table card | `fetchTableDetail` | `GET` | `/api/v1/schema/tables/{table_name}` | `table_name: string` (path) | None | `get_table` (`schema.py:114`) | Looks up table in catalog; case-insensitive fallback; builds column stats | `TableModel` (`columns`, `foreign_keys`, `indexes`, `primary_key_columns`) | Validated via `TableDetailResponseSchema`; populates right-pane column grid & FK lineage | Throws `ResourceNotFoundError`; UI shows error with available tables list |
| **6** | Conversational BI | User clicks "Ask Agent" or starter query | `streamChatQuery` | `POST` | `/api/v1/chat/stream` | None | `{"query": string, "session_id": string}` | `stream_chat_query` (`chat.py:49`) | Async pipeline: Router -> Gate -> Clarification -> Planner -> Grounder -> SQL -> Guardrail -> Executor -> Verifier -> Composer | Server-Sent Events (`text/event-stream`): `progress`, `result`, `error`, `done` | Custom stream reader splits on `\n\n`, parses SSE events; live stepper updates on `progress`; updates turn state on `result` | **Resilient Fallback:** If stream terminates without result payload or throws, immediately falls back to REST `executeChatQuery` |
| **7** | Conversational BI | Streaming fallback or REST call | `executeChatQuery` | `POST` | `/api/v1/chat/query` | None | `{"query": string, "session_id": string}` | `execute_chat_query` (`chat.py:26`) | Executes `multi_agent_orchestrator.run()` synchronously; returns complete result payload | `MultiAgentWorkflowResult` (Complete workflow DAG and artifacts) | Validated via `MultiAgentWorkflowResponseSchema`; sets turn `isStreaming=false` and saves result | Displays red "Execution Interrupted" card with error message |
| **8** | Observability | Tab switch & 10s interval | `fetchObservabilityMetrics` | `GET` | `/api/v1/ops/metrics` | None | None | `get_metrics` (`ops.py:17`) | Computes p50, p95, p99 latencies, run counts, and error class breakdown from `agent_app.sqlite` | `ObservabilityMetrics` (`total_runs`, `success_rate_pct`, `latency_p50_ms`, `error_classes_breakdown`) | Validated via `ObservabilityMetricsResponseSchema`; updates 7 KPI cards | Throws error; cards default to 0 / fallback values |
| **9** | Observability | Tab switch & 10s interval | `fetchRecentTraces` | `GET` | `/api/v1/ops/traces` | `limit: number = 25` (query) | None | `list_traces` (`ops.py:28`) | Queries `agent_app.sqlite` for the most recent 25 query execution traces | `RunTraceRecord[]` (`run_id`, `query`, `intent`, `latency_ms`, `verification_status`, `sql_executed`) | Validated via `RunTraceListResponseSchema`; populates traces table | Throws error; renders empty state banner |
| **10** | Unused in UI (Declared in `api.ts`) | Available for semantic search | `searchRetrieval` | `POST` | `/api/v1/retrieval/search` | None | `{"query": string, "top_k": number}` | `search_retrieval` (`retrieval.py:28`) | Hybrid BM25 + TF-IDF RRF retrieval (k=60), value linking, and semantic metric matching | `RetrievalDiagnosticPayload` (`hybrid_result`, `linked_values`, `relevant_metrics`) | Validated via `RetrievalDiagnosticResponseSchema` | None (function unused in current UI) |
| **11** | Unused in UI (Declared in `api.ts`) | Available for metric glossary | `fetchBusinessMetrics` | `GET` | `/api/v1/retrieval/metrics` | None | None | `list_metrics` (`retrieval.py:51`) | Lists verified business metric definitions, formulas, and primary tables | `BusinessMetric[]` (`name`, `display_name`, `formula_sql`, `plain_description`) | Validated via `BusinessMetricsListResponseSchema` | None (function unused in current UI) |
| **12** | Unused in UI (Declared in `api.ts`) | Available for session list | `fetchSessions` | `GET` | `/api/v1/memory/sessions` | `user_id: string` (query) | None | `list_sessions` (`memory.py:30`) | Queries `agent_app.sqlite` for conversation sessions | `SessionModel[]` (`session_id`, `title`, `created_at`, `updated_at`) | Validated via `SessionListResponseSchema` | None (function unused in current UI) |
| **13** | Unused in UI (Declared in `api.ts`) | Available for session restore | `fetchSessionDetail` | `GET` | `/api/v1/memory/sessions/{session_id}` | `session_id: string` (path) | None | `get_session` (`memory.py:41`) | Reads session metadata and 20 recent conversation turns | `{ session: SessionModel, turns: TurnModel[] }` | Validated via `SessionDetailResponseSchema` | None (function unused in current UI) |
| **14** | Unused in UI (Declared in `api.ts`) | Available for clearing history | `clearSessionApi` | `POST` | `/api/v1/memory/sessions/{session_id}/clear` | `session_id: string` (path) | None | `clear_session` (`memory.py:54`) | Clears turns and resets active memory frame in `agent_app.sqlite` | `{"session_id": string, "cleared": boolean}` | Returns boolean `json.success` | None (function unused in current UI; "+ New Session" generates a new random ID locally instead) |

---

## 3. End-to-End Execution Traces

### Trace 1: Natural Language Question to Rendered Answer & Visualization

```
1. User Action:
   User clicks starter query "What are our total sales and order counts by year?" in ChatInterface.tsx.

2. Client Event Handler (ChatInterface.tsx:127):
   executeQueryTurn(text) generates a new turnId ("turn-xxxx") and creates ChatTurn in React state.
   Sets isStreaming = true, activeStepKey = "understanding_question".

3. Client API Invocation (lib/api.ts:179):
   Calls streamChatQuery(qText, sessionId, onProgress, onResult, onError).
   Constructs POST request to http://localhost:8001/api/v1/chat/stream with JSON payload:
   { "query": "What are our total sales and order counts by year?", "session_id": "sess-xxxx" }

4. Backend Request Handling (backend/app/main.py & chat.py:49):
   - RequestIdMiddleware assigns X-Request-ID.
   - stream_chat_query instantiates an asyncio.Queue and starts background workflow_task().
   - Returns EventSourceResponse wrapping event_generator().

5. Multi-Agent Pipeline Execution (backend/app/workflow/orchestrator.py:84):
   - Step 1 (ContextResolver): Checks session history in agent_app.sqlite; outputs standalone query.
   - Step 2 (Router): Classifies intent as "trend", complexity "simple" (fires progress event).
   - Step 3 (AnswerabilityGate): Validates question against temporal (2023-2025) and domain boundaries (is_answerable=true).
   - Step 4 (Planner): Decomposes query into 7-step execution DAG.
   - Step 5 (HybridRetriever): BM25 + TF-IDF RRF retrieves "orders" table schema.
   - Step 6 (SQLGenerator): Generates:
     SELECT strftime('%Y', order_purchase_timestamp) AS year,
            COUNT(*) AS order_count,
            ROUND(SUM(total_amount), 2) AS total_sales
     FROM orders
     WHERE status = 'delivered'
     GROUP BY year
     ORDER BY year ASC;
   - Step 7 (AST Guardrail): sqlglot parses AST, verifies SELECT-only, checks allowlisted tables.
   - Step 8 (ReadOnlyRunner): Executes query on ecommerce.sqlite (mode=ro). Returns 3 rows.
   - Step 9 (Verifier & Chart Spec): Verifies row bounds, selects "line" chart, constructs Plotly spec.
   - Step 10 (ExecutiveComposer): Synthesizes executive narrative with bullet points, limitations, and 3 follow-ups.
   - Step 11 (ObservabilityTracer): Logs run latency (p50/p95), intent, and status in agent_app.sqlite.

6. SSE Stream Delivery:
   Server pushes progress events:
   event: progress\ndata: {"step": "understanding_question", "message": "Analyzing query..."}\n\n
   event: progress\ndata: {"step": "retrieving_schema", "message": "Retrieving schema..."}\n\n
   event: progress\ndata: {"step": "generating_query", "message": "Generating SQL..."}\n\n
   ...
   event: result\ndata: { <MultiAgentWorkflowResult JSON> }\n\n
   event: done\ndata: {"status": "completed"}\n\n

7. Client Stream Parsing (lib/api.ts:205-259):
   - Reader receives byte chunks, normalizes CRLF to LF, parses "event:" and "data:".
   - onProgress updates completedSteps and activeStepKey.
   - onResult receives MultiAgentWorkflowResult, dispatches state update:
     turn.result = result; turn.isStreaming = false; turn.activeTab = "narrative".

8. UI Rendering:
   - ChatInterface renders Completed Result Card with badges.
   - Narrative tab displays composed_answer text.
   - PlotlyChartRenderer mounts dynamically, imports plotly.js-dist-min, renders dark-themed Plotly chart.
   - Bottom renders 3 clickable follow-up suggestion buttons.
```

---

### Trace 2: Schema Introspection & Asynchronous Preparation

```
1. User Action:
   User clicks "Run Preparation" in SchemaReadinessSection.tsx.

2. Client Event Handler (SchemaReadinessSection.tsx:104):
   Calls prepareMutation.mutate(false).

3. Client API Invocation (lib/api.ts:52):
   Calls triggerSchemaPreparation(false) -> POST /api/v1/schema/prepare?force=false.

4. Backend Execution (backend/app/schema/job.py:46 & service.py:102):
   - Computes SHA-256 fingerprint of ecommerce.sqlite.
   - If cache matches and force=false, immediately returns completed job state.
   - If profiling required, spawns background asyncio task iterating through all 30 tables:
     Runs PRAGMA table_info, PRAGMA foreign_key_list, PRAGMA index_list, column null rates, and sample ranges.
     Updates job_state.progress_percent from 0 to 100.

5. Client Polling:
   TanStack Query refetchInterval switches to 1,500ms while status is "pending" or "running".
   Fires GET /api/v1/schema/status every 1.5 seconds.
   UI displays animated progress bar and current table name.

6. Completion:
   When status === "succeeded", progress bar completes.
   TanStack Query invalidates ["schemaStatus"] and ["schemaTables"].
   Left-pane table list and summary KPI strip refresh automatically.
```

---

## 4. Error Mapping & Status Codes

| HTTP Status | Error Code | Backend Condition | Client Exception / UI Behavior |
|---|---|---|---|
| `200 OK` | N/A | Successful operation | Envelope `success: true`; data parsed with Zod and rendered |
| `503 Service Unavailable` | N/A | Readiness probe failure (`get_readiness`) | Envelope `success: false`; `HealthReadinessCard` shows "Backend Offline" card with terminal instructions |
| `400 Bad Request` | `VALIDATION_ERROR` | Malformed request body (Pydantic validation failure) | Displayed in red error banner in ChatInterface |
| `404 Not Found` | `RESOURCE_NOT_FOUND` | Table name does not exist in schema catalog | Displayed in Schema Explorer; details list valid tables |
| `400 Bad Request` | `SQL_GUARDRAIL_VIOLATION` | Adversarial injection or forbidden SQL keyword detected | Blocked by ast_guardrail; verification status set to "blocked"; recorded in telemetry |
| `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | Unhandled Python exception | Envelope `success: false`; logged in agent_app.sqlite; ChatInterface triggers REST fallback |

---

## 5. Declared but Unused API Functions

The following functions are implemented in `frontend/src/lib/api.ts` with complete Zod schemas, but have no corresponding UI trigger in `ChatInterface.tsx` or `page.tsx`:

1. `fetchBusinessMetrics()`: Fetches semantic metric definitions from `/api/v1/retrieval/metrics`.
   - *Redesign Opportunity:* Surface in a new "Metric Glossary" modal or sidebar.
2. `searchRetrieval(query, topK)`: Executes hybrid BM25 + embedding retrieval diagnostics from `/api/v1/retrieval/search`.
   - *Redesign Opportunity:* Expose in an "Advanced Retrieval Debugger" panel inside the Schema tab.
3. `fetchSessions()` & `fetchSessionDetail(sessionId)`: Fetches past conversation sessions and turn transcripts from `/api/v1/memory/sessions`.
   - *Redesign Opportunity:* Build a collapsible "Conversation History" sidebar similar to ChatGPT or Claude.
4. `clearSessionApi(sessionId)`: Deletes session turns on the backend via `/api/v1/memory/sessions/:id/clear`.
   - *Redesign Opportunity:* Wire up to the "+ New Session" button to clear server state when requested by user.

---
*End of Deliverable 2 (Integration Map)*

