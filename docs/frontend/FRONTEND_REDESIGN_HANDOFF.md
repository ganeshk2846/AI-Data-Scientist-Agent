# Frontend Redesign Handoff & Implementation Specification
**AI for BI — Data Scientist Agent**
*Architectural Directives, Preservation Invariants, Redesign Opportunities & Acceptance Criteria*
*Intended Audience: Autonomous AI Frontend Coding / Design Tool*

---

## 1. Executive Briefing for Redesign Tool

You are tasked with redesigning and modernizing the frontend user experience for the **AI for BI Data Scientist Agent**.
The backend is a production-grade FastAPI application connected to an immutable SQLite data warehouse (`ecommerce.sqlite`, 30 tables, 334,503 rows).

**Your mission is to upgrade the UI/UX to modern, world-class enterprise SaaS standards while strictly preserving 100% of the existing backend API contracts, business logic, safety invariants, and data models.**

---

## 2. Inviolable Preservation Invariants (DO NOT BREAK)

When redesigning the frontend, the following rules and contracts **must never be violated or removed**:

1. **Strict Source Immutability:**
   - The warehouse database `ecommerce.sqlite` is strictly read-only (`mode=ro`).
   - The frontend must never offer, generate, or execute `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or other mutating SQL queries.
2. **API Contract & Schema Compatibility:**
   - Every request and response payload must conform to the Zod schemas defined in `frontend/src/types/api.ts`.
   - Never remove or alter the fields of `MultiAgentWorkflowResult`, `ReadinessStatus`, `SchemaStatus`, `TableModel`, or `ObservabilityMetrics`.
3. **SSE Streaming Protocol:**
   - The real-time question stream relies on Server-Sent Events from `POST /api/v1/chat/stream`.
   - The stream events `progress` (JSON with `step` and `message`), `result` (full `MultiAgentWorkflowResult`), `error`, and `done` must be processed as implemented in `frontend/src/lib/api.ts`.
   - The resilient fallback to REST `POST /api/v1/chat/query` must be retained in case streaming disconnects.
4. **Plotly.js Dynamic Client-Side Import:**
   - Plotly.js (`plotly.js-dist-min`) uses browser-only global DOM/SVG APIs.
   - It **must never be imported at the module root of a server-rendered component**. Always use dynamic `import("plotly.js-dist-min")` inside `useEffect` or Next.js `dynamic(..., { ssr: false })`.
5. **Multi-Turn Context & Session ID Propagation:**
   - The backend `ContextResolver` relies on a unique `session_id` string transmitted in every chat request (`body: { query, session_id }`).
   - Multi-turn rewrites depend on consistent session IDs.
6. **AST Bounded Repair Visibility:**
   - When SQL repairs occur (`res.repair_attempts.length > 0`), the UI must display the repair count and trail to maintain transparency.
7. **Answerability Refusal & Clarification Handling:**
   - When `res.answerability.is_answerable === false`, the UI must display the honest refusal reason and supported domains.
   - When `res.clarification.needs_clarification === true`, the UI must display the ambiguity explanation and allow one-click selection of options.

---

## 3. What Can Safely Be Redesigned

You have full creative and architectural freedom to redesign, reorganize, and enhance the following areas:

1. **Information Architecture & Layout:**
   - Transition from a single tabbed page (`page.tsx`) to Next.js App Router subroutes:
     - `/chat` (or `/` default) — Conversational BI workspace
     - `/schema` — Data Warehouse Catalog & ERD Visualizer
     - `/observability` — Telemetry & Latency Dashboard
     - `/system` — System Health & Diagnostics
   - Alternatively, implement a persistent left-hand collapsible sidebar navigation (like modern AI workspaces: ChatGPT, Claude, Cursor, Databricks Lakeview).
2. **Conversation History Sidebar:**
   - Implement a collapsible sidebar showing past conversation sessions using the already implemented backend endpoints (`fetchSessions`, `fetchSessionDetail`, `clearSessionApi` in `frontend/src/lib/api.ts`).
3. **Component Decomposition:**
   - Break down the 1,116-line `ChatInterface.tsx` into clean, modular components:
     - `ChatInput.tsx` (Input with prompt suggestions, file upload placeholder, mic/voice UI)
     - `ChatThread.tsx` (Virtual list or smooth-scrolling message turns)
     - `ChatTurnCard.tsx` (User message bubble + Agent response container)
     - `DagProgressStepper.tsx` (Modern animated DAG execution graph)
     - `ArtifactCard.tsx` (Tabs for Executive Answer, Plotly Chart, ML Tool Artifacts, AST SQL, and Data Table)
     - `ClarificationPrompt.tsx` (Modern interactive card)
     - `RefusalBanner.tsx` (Domain guidance banner)
4. **Visual Design & Design System:**
   - Upgrade visual styling: subtle glassmorphism, refined micro-borders (`border-white/10`), modern typography scales (Inter / Geist font), refined badges, and responsive tables.
   - Add theme toggle support (Dark / Light / System) if desired, provided high contrast is maintained.
5. **Interactive Data Tables:**
   - Replace simple HTML table with an interactive data grid supporting client-side pagination, sorting, column search, and density toggles.
6. **ERD / Schema Graph Visualization:**
   - In the Schema Explorer, upgrade the Foreign Key list to an interactive schema relationship diagram (using SVG, Mermaid, or React Flow).
7. **Semantic Business Metrics Glossary:**
   - Build a UI drawer or modal connecting to the unused `fetchBusinessMetrics()` endpoint to expose enterprise formulas (e.g. Gross Revenue, Net Revenue, AOV, Churn Rate).

---

## 4. Key Source Code File Map

| Purpose / Feature | Primary Source Files |
|---|---|
| **App Entry & Root Layout** | `frontend/src/app/layout.tsx`, `frontend/src/app/providers.tsx`, `frontend/src/app/globals.css` |
| **Current View Coordinator** | `frontend/src/app/page.tsx` |
| **Application Header** | `frontend/src/components/Header.tsx` |
| **Conversational BI Interface** | `frontend/src/components/ChatInterface.tsx` |
| **Plotly Chart Engine** | `frontend/src/components/PlotlyChartRenderer.tsx` |
| **Data Warehouse & Schema Explorer** | `frontend/src/components/SchemaReadinessSection.tsx` |
| **Telemetry & Observability Dashboard** | `frontend/src/components/ObservabilityDashboard.tsx` |
| **System Health Card** | `frontend/src/components/HealthReadinessCard.tsx` |
| **API Client & SSE Stream** | `frontend/src/lib/api.ts` |
| **TypeScript Types & Zod Schemas** | `frontend/src/types/api.ts` |
| **Next.js & Tailwind Config** | `frontend/next.config.mjs`, `frontend/tailwind.config.ts`, `frontend/package.json` |

---

## 5. Implementation Checklist for Frontend Redesign

Use this sequential checklist to verify that all functional requirements are satisfied during the redesign:

- [ ] **Step 1: Environment & Base URL Standardization**
  - Verify `API_BASE_URL` in `frontend/src/lib/api.ts`.
  - Ensure development works via relative `/api/backend` or direct `NEXT_PUBLIC_API_URL`.
- [ ] **Step 2: Navigation & Shell Overhaul**
  - Implement a polished application shell (Header + Navigation Sidebar or Top Bar).
  - Retain the live backend health status indicator (`isReady` from `GET /api/v1/ready`).
  - Retain application version badge.
- [ ] **Step 3: Conversational BI Modularization**
  - Split `ChatInterface.tsx` into modular components.
  - Retain Server-Sent Events streaming from `POST /api/v1/chat/stream` with the 7-stage DAG progress stepper.
  - Retain REST fallback to `POST /api/v1/chat/query`.
  - Retain the 7 starter query pills.
  - Retain interactive clarification cards and honest refusal banners.
  - Retain the 3 clickable follow-up suggested questions at the bottom of each turn.
- [ ] **Step 4: Artifact Tabs & Renderers**
  - **Narrative Tab:** Formatted text, citations, key findings grid, caveats box, and "Copy Narrative" button.
  - **Chart Tab & Preview:** Plotly chart renderer with PNG download, dynamic browser import, and resize listener.
  - **Analysis Tab:** Render all 4 deterministic ML tool results:
    - Customer Churn Risk table (Wilson score intervals, revenue at risk).
    - Anomaly Detection table (z-scores, quality flags).
    - Time-series Forecast table (point forecast, 80%/95% prediction intervals, backtest metrics).
    - Budget Optimization table (SLSQP allocations, expected return).
  - **SQL Tab:** Syntax-highlighted SQLite query, "Copy SQL" button, and Bounded Repair trail.
  - **Data Tab:** Interactive table, row count, execution latency, "Export CSV", and "Export JSON".
  - **DAG & Trace Tabs:** Step breakdown, statuses, and millisecond durations.
- [ ] **Step 5: Schema Catalog & Profiler**
  - Left pane table list with instant text search and row count badges.
  - Right pane table inspector with columns, types, constraint badges (PK, FK, Date, Num, NN), null rate colors, distinct counts, sample ranges, and foreign key lineage mappings.
  - "Run Preparation" and "Force Refresh" buttons with animated progress bar during active jobs.
- [ ] **Step 6: Observability & Telemetry**
  - 7 KPI cards: Total Runs, Success Rate (%), Latency p50, p95, p99, Average Latency, and Security Blocks.
  - Error class breakdown badges.
  - Recent traces table with color-coded latencies (<1s green, 1-3s yellow, >3s red), verification status badges, and "Copy SQL" buttons.
  - "Refresh Telemetry" button with spin animation.
- [ ] **Step 7: Surfaces for Unused API Endpoints (New Value)**
  - Integrate conversation session list via `fetchSessions()` and `fetchSessionDetail()`.
  - Connect "+ New Session" or "Clear History" to `clearSessionApi()`.
  - Add a Semantic Metric Glossary modal or drawer via `fetchBusinessMetrics()`.
- [ ] **Step 8: Verification & Quality Assurance**
  - Run `npx tsc --noEmit` — must compile with 0 TypeScript errors.
  - Run `npm run build` — must build production bundle cleanly.
  - Run `npm run test` — must pass contract validation check.

---

## 6. Acceptance Criteria

Any redesigned frontend will be evaluated against the following strict acceptance criteria:

1. **Compilation & Type Safety:** `npx tsc --noEmit` and `npm run build` complete with **zero errors and zero warnings**.
2. **Contract Fidelity:** 100% of data rendered in the UI is parsed and validated by existing Zod schemas in `types/api.ts`. No schemas are bypassed with `any`.
3. **No Database Writes:** No frontend action attempts to write or mutate `ecommerce.sqlite`.
4. **Streaming Reliability:** Streaming progress updates live via SSE without UI freezing, with seamless fallback to REST on failure.
5. **Chart Fidelity:** Plotly charts render cleanly in dark mode and can be downloaded as PNG without crashing server-side rendering.
6. **Data Export Integrity:** Export CSV produces RFC 4180 compliant CSV files with correct column headers and quoted fields; Export JSON produces formatted JSON arrays.
7. **Accessibility & Responsiveness:** All interactive controls are keyboard focusable, contrast ratios meet WCAG AA/AAA standards, and the interface operates smoothly from mobile (375px) to ultra-wide desktop (1920px+).

---
*End of Deliverable 5 (Redesign Handoff)*

