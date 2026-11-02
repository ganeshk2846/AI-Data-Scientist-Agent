# 06 — Analytics, Frontend, and Integration Audit

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Senior Data Analyst, Frontend Architect, Full-Stack Integration Engineer  
**Scope:** Complete inspection of deterministic analysis tools, machine learning models, frontend single-page architecture, route definitions, component hierarchies, state management, and frontend-to-backend integration contracts.

---

## 1. AI Data Analyst Tool Capabilities

The application implements a central analysis tool registry in [`backend/app/analysis/registry.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/registry.py) providing **7 deterministic statistical and machine learning tools**:

| Tool Name | Analysis Type | Implementation File | Inputs Required | Underlying Algorithm / Library |
| :--- | :--- | :--- | :--- | :--- |
| `compare_periods` | Period Comparison | [`analysis/descriptive.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/descriptive.py) | `records`, `metric_col`, `period_col`, `period_a_val`, `period_b_val` | Deterministic variance & mix contribution calculation (Pandas). |
| `detect_anomalies`| Anomaly Detection | [`analysis/anomalies.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/anomalies.py) | `records`, `date_col`, `metric_col`, `threshold` | Robust median / Median Absolute Deviation (MAD) z-score screening. |
| `analyze_drivers` | Driver Analysis | [`analysis/diagnostic.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/diagnostic.py) | `records`, `metric_col`, `dimension_col` | Variance decomposition along categorical dimensions; non-causal disclaimer. |
| `forecast_series` | Forecasting | [`analysis/forecasting.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/forecasting.py) | `records`, `date_col`, `value_col`, `horizon_periods` | Holt-Winters exponential smoothing & seasonal-naive baseline with 80%/95% CIs. |
| `simulate_scenario`| Scenario Simulation | [`analysis/scenarios.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/scenarios.py) | `baseline_value`, `parameter_name`, `shock_pct`, `elasticity` | Price elasticity parameter simulation ($E = \Delta Q\% / \Delta P\%$) with sensitivity bounds. |
| `analyze_customer_churn_risk` | Churn Risk | [`analysis/churn.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/churn.py) | None (queries SQLite directly) | Wilson score 95% confidence intervals over customer segment transitions. |
| `optimize_budget_allocation`| Prescriptive Optimization | [`analysis/optimization.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/analysis/optimization.py) | `total_budget`, `channels`, `historical_roas` | Constrained convex optimization via `scipy.optimize.minimize` (SLSQP). |

### 1.1 Tool Portability & Coupling Analysis
- **Generic Tools (Portable):** `compare_periods`, `detect_anomalies`, `analyze_drivers`, and `forecast_series` operate entirely in memory on generic lists of record dictionaries (`List[Dict[str, Any]]`). They do **not** assume any database table or schema and are completely database-agnostic.
- **Tightly Coupled Tools:**
  - `analyze_customer_churn_risk`: Executes hardcoded SQL against `customer_segment_history`, `customer_segments`, and `orders`. Fails if tables are renamed (e.g. `customer_segments_history` in `novacart_ecommerce.db`).
  - `simulate_scenario` & `optimize_budget_allocation`: The underlying functions are pure math, but in [`backend/app/workflow/orchestrator.py#L515-L529`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L515-L529), they are invoked with hardcoded dummy values (`baseline_value=1000000.0`, `total_budget=50000.0`, channels `["Search", "Social", "Email", "Affiliate"]`) rather than extracting parameters from the user's natural language question.

---

## 2. Complete Frontend Architecture

### 2.1 Technology & Framework
- **Framework:** Next.js 14.2.15 (React 18.3.1, TypeScript 5.4.3).
- **Architecture:** Client-side rendered Single-Page Application (SPA) using Next.js App Router (`frontend/src/app/page.tsx`).
- **Styling:** Tailwind CSS with custom slate-950 dark theme palette, glassmorphism cards, and Lucide icons.
- **Server State & Data Fetching:** TanStack React Query (`^5.28.9`) managing asynchronous fetching, refetch intervals (15s health polling), and cache invalidation.

### 2.2 Complete Route Inventory
| Route Path | Type | Source Component | Purpose & Implemented Capabilities |
| :--- | :--- | :--- | :--- |
| `/` | Page (SPA) | [`frontend/src/app/page.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/app/page.tsx) | Unified application dashboard hosting 4 functional tabs controlled by local state and `?tab=` query parameter: **chat**, **schema**, **observability**, **system**. |
| `/api/*` | Proxy | Next.js API Rewrite (optional) | Direct HTTP/SSE communication to FastAPI at `http://localhost:8001`. |

*Note: No separate sub-pages, nested routes, or dynamic URL segments exist. The entire frontend operates within `/`.*

---

## 3. UI Component Hierarchy and Tab Specifications

```
HomePage (app/page.tsx)
  │
  ├── Header (Header.tsx)
  │     Displays application title, version (v0.1.0), "mode=ro" badge, and backend readiness indicator.
  │
  ├── Navigation Bar (Tab Switcher)
  │     Tabs: [1. Conversational BI] [2. Data Warehouse & Schema] [3. Telemetry & Latency] [4. System Health]
  │
  ├── [Tab 1: ChatInterface] (components/ChatInterface.tsx)
  │     ├── SessionsDrawer (components/chat/SessionsDrawer.tsx) — Session list, creation, and clearing.
  │     ├── ChatMessageTurn (components/chat/ChatMessageTurn.tsx) — User query turn and AI response turn.
  │     │     ├── StreamingStepper (components/chat/StreamingStepper.tsx) — Real-time SSE execution DAG stepper.
  │     │     ├── RefusalBanner (components/chat/RefusalBanner.tsx) — Displays abstention/refusal cards.
  │     │     ├── ClarificationPrompt (components/chat/ClarificationPrompt.tsx) — Interactive ambiguity buttons.
  │     │     ├── ArtifactCard (components/chat/ArtifactCard.tsx) — Tabbed view: [Chart / Data Grid / SQL / Trace].
  │     │     │     ├── PlotlyChartRenderer (components/PlotlyChartRenderer.tsx) — Plotly.js chart renderer.
  │     │     │     ├── DataTable (components/ui/DataTable.tsx) — Paginated, searchable result grid.
  │     │     │     └── Code block — Syntax-highlighted SQL with copy button.
  │     │     └── AnalysisArtifacts (components/chat/AnalysisArtifacts.tsx) — ML cards (Forecast, Anomaly, etc.).
  │     └── ChatInput (components/chat/ChatInput.tsx) — Natural language input, prompt suggestions, submit button.
  │
  ├── [Tab 2: SchemaReadinessSection] (components/SchemaReadinessSection.tsx)
  │     ├── Schema Preparation Trigger Button (POST /api/v1/schema/prepare?force=true).
  │     ├── Progress Bar & Summary Cards (Tables count, total rows, last profiled).
  │     └── Tables List & Column Profile Inspector (Null rates, PK/FK flags, distinct counts, sample values).
  │
  ├── [Tab 3: ObservabilityDashboard] (components/ObservabilityDashboard.tsx)
  │     ├── Summary Cards: Total Runs, Success Rate %, p50 Latency, p95 Latency, Security Blocks.
  │     └── Recent Traces Table: Run ID, query, intent, execution latency, row count, status.
  │
  └── [Tab 4: HealthReadinessCard & Pipeline] (components/HealthReadinessCard.tsx)
        ├── Readiness Diagnostics: Database status, LLM configuration, store status.
        └── Visual 10-Step Architecture Pipeline: Interactive step-by-step pipeline overview.
```

---

## 4. Frontend-to-Backend API Integration Map

| Frontend Service / Hook | HTTP Protocol | Backend Endpoint | Request Payload | Response Data | Error Handling |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `fetchReadiness()` in `lib/api.ts` | GET | `/api/v1/ready` | None | `ReadinessStatus` (connected, read_only, llm, tables) | Returns disconnected state; Header shows warning. |
| `streamChatQuery()` in `lib/api.ts` | POST (SSE) | `/api/v1/chat/stream` | `{query: string, session_id?: string}` | Stream of SSE events: `progress`, `result`, `error`, `done` | Terminates stream; displays error card in message turn. |
| `submitChatQuery()` in `lib/api.ts` | POST | `/api/v1/chat/query` | `{query: string, session_id?: string}` | `MultiAgentWorkflowResult` | Fallback REST mode; renders refusal or error banner. |
| `fetchCatalog()` in `lib/api.ts` | GET | `/api/v1/schema/catalog` | None | `DatabaseCatalog` (all 30/46 tables, columns, FK graph) | Displays error message in schema tab with retry button. |
| `triggerSchemaPreparation()` | POST | `/api/v1/schema/prepare` | Query param `?force=bool` | `PreparationJobState` (job_id, status, progress_percent) | Shows failure alert; polling stops. |
| `fetchSchemaJobStatus()` | GET | `/api/v1/schema/jobs/{id}` | None | `PreparationJobState` | Polls until `succeeded` or `failed`. |
| `fetchObservabilityMetrics()`| GET | `/api/v1/ops/metrics` | None | `ObservabilityMetrics` (p50, p95, success_rate) | Graceful fallback to zeros. |
| `fetchRecentTraces()` | GET | `/api/v1/ops/traces` | Query param `?limit=25` | `List[RunTraceRecord]` | Empty state shown in traces table. |
| `fetchSessions()` | GET | `/api/v1/memory/sessions` | None | `List[SessionModel]` | Shows empty sessions list in drawer. |
| `clearSession()` | POST | `/api/v1/memory/sessions/{id}/clear`| None | `{success: bool}` | Resets active conversation turn state. |

---

## 5. State, Isolation, and Multi-Database Limitations in Frontend

1. **Absence of Database Selector:**
   - There is **no UI component, dropdown, or modal** allowing the user to view registered databases, add a new database connection, or switch between `ecommerce.sqlite` and `novacart_ecommerce.db`.
   - The frontend assumes whatever database the backend serves is the only database in existence.
2. **Session Scoping Defect:**
   - Sessions listed in `SessionsDrawer` store `session_id`, `title`, and `created_at`.
   - No `database_id` is associated with any session or chat turn.
   - If the backend database changes, previous chat threads referencing old schema entities remain visible and active in the UI.
3. **Optimistic Updates & SSE Stream Resilience:**
   - The SSE stream implementation in `ChatInterface.tsx` correctly handles partial steps (`StreamingStepper`), updating the DAG visualization step-by-step as events arrive from the backend.
   - If the backend aborts or throws an exception, the SSE stream emits an `event: error` and the UI transitions from loading to an error state cleanly.

---

## 6. Summary of Frontend and Integration Findings

| Finding ID | Finding Description | Severity | Confidence | Source File & Line |
| :--- | :--- | :--- | :--- | :--- |
| **FRONT-01**| Zero database connection management in UI; no connection form, selector, or database status switch. | High | **VERIFIED** | [`page.tsx:71-96`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/app/page.tsx#L71-L96) |
| **FRONT-02**| Conversation sessions and message histories have no database ID scoping in frontend state or API payloads. | Medium | **VERIFIED** | [`api.ts:20-23`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/lib/api.ts#L20-L23), [`SessionsDrawer.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/components/chat/SessionsDrawer.tsx) |
| **FRONT-03**| Analysis tools `simulate_scenario` and `optimize_budget_allocation` run on hardcoded dummy parameters rather than UI-driven inputs. | Medium | **VERIFIED** | [`orchestrator.py:515-529`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L515-L529) |
| **FRONT-04**| Real-time SSE streaming, interactive Plotly visualization, and tabular data pagination are fully implemented and verified. | Positive | **VERIFIED** | [`ChatInterface.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/components/ChatInterface.tsx), [`PlotlyChartRenderer.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/components/PlotlyChartRenderer.tsx) |
| **FRONT-05**| Schema profiling progress bar accurately reflects backend job polling via `GET /api/v1/schema/jobs/{id}`. | Positive | **VERIFIED** | [`SchemaReadinessSection.tsx`](file:///c:/D_drive/AI_FOR_BI_P/frontend/src/components/SchemaReadinessSection.tsx) |

