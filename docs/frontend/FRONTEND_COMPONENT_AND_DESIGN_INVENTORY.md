# Frontend Component & Design System Inventory
**AI for BI — Data Scientist Agent**
*UI/UX Design Tokens, Component Specifications, and Reusability Guide*

---

## 1. Design System Tokens & Styling Architecture

The application implements a custom dark enterprise theme utilizing Tailwind CSS 3.4.

### 1.1 Color Palette & Theme Tokens
Configured in `frontend/tailwind.config.ts` and `frontend/src/app/globals.css`:

| Token Name | Hex Value | Usage / Semantic Role | Evidenced CSS Classes |
|---|---|---|---|
| `background` | `#090d16` | Main application background (Deep Obsidian Navy) | `bg-background`, `var(--background)` |
| `foreground` | `#f1f5f9` | Primary body typography (Slate 100) | `text-foreground`, `var(--foreground)` |
| `card` | `#0f172a` | Elevated surface containers, panels, cards (Slate 900) | `bg-card`, `bg-card/60`, `bg-card/40` |
| `card-foreground` | `#f8fafc` | High-contrast headers on card surfaces (Slate 50) | `text-card-foreground` |
| `border` | `#1e293b` | Structural dividers, card borders, table borders (Slate 800) | `border-border`, `border-border/50` |
| `primary` | `#3b82f6` | Brand accent, active tabs, action buttons, links (Blue 500) | `bg-primary`, `text-primary`, `border-primary` |
| `primary-foreground`| `#ffffff` | Text on primary buttons and user bubbles | `text-white` |
| `muted` | `#1e293b` | Subtle button backgrounds, secondary pills | `bg-muted`, `bg-muted/60`, `bg-muted/40` |
| `muted-foreground` | `#94a3b8` | Subtitles, labels, secondary metadata (Slate 400) | `text-muted-foreground` |
| `success` | `#10b981` | Online indicators, verified checks, positive metrics (Emerald 500) | `bg-success`, `text-success`, `border-success/30` |
| `warning` | `#f59e0b` | Caveats, cautions, repair indicators, z-scores (Amber 500) | `bg-warning`, `text-warning`, `border-warning/30` |
| `destructive` | `#ef4444` | High null rates, revenue at risk, error alerts (Red 500) | `bg-destructive`, `text-destructive`, `border-destructive/40` |

### 1.2 Typography Hierarchy
- **Base Font Family:** `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif` (`app/globals.css:13`).
- **Monospace Font Family:** `ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace` (`font-mono`). Extensively used for SQL queries, table names, row counts, millisecond latencies, session IDs, and numeric metrics.
- **Type Scale:**
  - `text-lg` (18px / 28px): Main card headers, table inspector title.
  - `text-base` (16px / 24px): Section titles, budget optimization values.
  - `text-sm` (14px / 20px): Chat question input text, subcomponent headers.
  - `text-xs` (12px / 16px): Standard interface body, table cells, tab labels, button text.
  - `text-[11px]` (11px / 14px): Micro-metadata, timestamps, table constraints, code pills.
  - `text-[10px]` (10px / 12px): Constraint badges (PK, FK), DAG step numbers, badge pills.

### 1.3 Surface, Radius & Shadow Conventions
- **Rounded Corners:**
  - `rounded-xl` (12px): Major cards, modal dialogs, chat question box, turn containers.
  - `rounded-lg` (8px): Action buttons, secondary panels, table containers, search inputs.
  - `rounded-md` (6px): Sub-tab buttons, badge pills.
  - `rounded-full` (9999px): Status dots, confidence indicators, count pills.
- **Surfaces & Backdrop Filters:**
  - Sticky nav bar and header use `bg-card/40 backdrop-blur` or `bg-card/60 backdrop-blur`.
  - Nested cards use `bg-background/40`, `bg-background/50`, or `bg-background/60` for depth.
- **Shadows:** Minimal usage (`shadow-sm`) to maintain a clean, flat, modern technical interface.

---

## 2. Categorized Component Inventory

### Category 1: Application Shell & Root Components

#### Component: `RootLayout`
- **File:** `frontend/src/app/layout.tsx`
- **Purpose:** Next.js root layout wrapper. Injects HTML `className="dark"`, applies body styles, and wraps children with `Providers`.
- **Props:** `{ children: React.ReactNode }`
- **Internal State:** None.
- **Dependencies:** `Providers`, `globals.css`.
- **Styling:** `bg-background text-foreground antialiased min-h-screen`.
- **Reusability:** App shell singleton.

#### Component: `Providers`
- **File:** `frontend/src/app/providers.tsx`
- **Purpose:** Configures and provides TanStack `QueryClientProvider` to the React tree.
- **Configuration:**
  - `staleTime: 5000` (5 seconds).
  - `refetchOnWindowFocus: false` (prevents unexpected background refetches).
  - `retry: 1` (single retry on network failure).
- **Props:** `{ children: ReactNode }`
- **Internal State:** `useState(() => new QueryClient(...))`.
- **Reusability:** Context provider singleton.

#### Component: `Header`
- **File:** `frontend/src/components/Header.tsx`
- **Purpose:** Top branding bar displaying application name, version pill, and live pulsating backend connectivity status indicator.
- **Props:**
  - `isReady?: boolean` (defaults to undefined).
  - `version?: string` (defaults to `"0.1.0"`).
- **Dependencies:** `lucide-react` (`Sparkles`).
- **Interactive Elements:** Pulsating status dot (`bg-success animate-pulse` vs `bg-warning`).
- **Reusability:** **High**. Clean, self-contained, fully reusable across any page or layout.

---

### Category 2: Major Workspace & Page Components

#### Component: `HomePage`
- **File:** `frontend/src/app/page.tsx`
- **Purpose:** Master tab controller and page layout. Manages the 4 primary application workspaces.
- **Internal State:**
  - `activeTab: "chat" | "schema" | "observability" | "system"` (defaults to `"chat"`).
- **TanStack Queries:**
  - `["readiness"]`: Polls `fetchReadiness()` every 15,000ms.
- **Components Rendered:**
  - `Header`
  - Sticky Tab Navigation Bar (`TABS.map(...)`)
  - Active workspace: `ChatInterface` | `SchemaReadinessSection` | `ObservabilityDashboard` | `HealthReadinessCard` + Pipeline Steps
  - Footer
- **Reusability:** Single-instance page coordinator.

#### Component: `ChatInterface`
- **File:** `frontend/src/components/ChatInterface.tsx`
- **Purpose:** Full multi-agent conversational BI workspace. Handles streaming queries, message history, Plotly charts, deterministic ML tool artifacts, SQL display, CSV/JSON export, and follow-up prompts.
- **Props:** None.
- **Internal State:**
  - `sessionId: string` (generated on mount).
  - `mounted: boolean` (SSR hydration guard).
  - `queryInput: string` (controlled text input).
  - `turns: ChatTurn[]` (conversational message history).
  - `isSubmitting: boolean` (network lock).
  - `copiedSqlId: string | null` (copy feedback timer).
  - `copiedNarrativeId: string | null` (copy feedback timer).
- **Refs:** `turnsEndRef = useRef<HTMLDivElement>(null)` (auto-scroll anchor).
- **Dependencies:** `PlotlyChartRenderer`, `lib/api.ts` (`executeChatQuery`, `streamChatQuery`), `types/api.ts`, `lucide-react` (20 icons).
- **Reusability:** **Monolithic Page-Coupled**. Should be broken down into modular components during redesign.

#### Component: `SchemaReadinessSection`
- **File:** `frontend/src/components/SchemaReadinessSection.tsx`
- **Purpose:** Interactive schema catalogue explorer and background profiling orchestrator.
- **Internal State:**
  - `selectedTableName: string | null` (defaults to `"orders"`).
  - `searchTerm: string` (filter input for table list).
- **TanStack Queries & Mutations:**
  - `useQuery(["schemaStatus"])`
  - `useQuery(["schemaTables"])`
  - `useQuery(["tableDetail", selectedTableName])`
  - `useMutation(triggerSchemaPreparation)`
- **Dependencies:** `lib/api.ts`, `types/api.ts`, `lucide-react`.
- **Reusability:** Standalone workspace component.

#### Component: `ObservabilityDashboard`
- **File:** `frontend/src/components/ObservabilityDashboard.tsx`
- **Purpose:** Production telemetry and latency percentile dashboard.
- **Internal State:**
  - `copiedSql: string | null` (copy feedback timer).
- **TanStack Queries:**
  - `useQuery(["observabilityMetrics"])` (10s polling).
  - `useQuery(["recentTraces"])` (10s polling).
- **Dependencies:** `lib/api.ts`, `types/api.ts`, `lucide-react`.
- **Reusability:** Standalone workspace component.

---

### Category 3: Visualizations & Data Renderers

#### Component: `PlotlyChartRenderer`
- **File:** `frontend/src/components/PlotlyChartRenderer.tsx`
- **Purpose:** Dynamically renders interactive dark-themed Plotly charts with resize handling, PNG export, view toggle (Chart vs Table), and tabular fallback.
- **Props:**
  - `chartSpec: ChartSpecification` (required).
  - `queryResult?: QueryExecutionResult | null` (optional, for table fallback).
- **Internal State:**
  - `viewMode: "chart" | "table"` (defaults to `"table"` if `chartSpec.fallback_to_table === true`).
  - `renderError: string | null`.
  - `isLoading: boolean`.
- **Lifecycle & Dynamic Import:**
  - Dynamically imports `plotly.js-dist-min` inside `useEffect` on the client only.
  - Adds window `resize` listener calling `plotlyInstance.Plots.resize`.
  - Cleanup calls `plotlyInstance.purge(containerRef.current)`.
- **Dependencies:** `plotly.js-dist-min`, `types/api.ts`, `lucide-react` (`BarChart2`, `Download`, `Eye`, `Table`).
- **Reusability:** **Very High**. Completely generic and cleanly decoupled from specific pages.

---

### Category 4: Diagnostic & Status Cards

#### Component: `HealthReadinessCard`
- **File:** `frontend/src/components/HealthReadinessCard.tsx`
- **Purpose:** Displays database immutability verification, table/row counts, database size, LLM provider status, and agent persistence store readiness.
- **Props:**
  - `data?: ReadinessStatus`
  - `isLoading: boolean`
  - `isError: boolean`
  - `error?: Error | null`
  - `onRefresh: () => void`
- **Dependencies:** `types/api.ts`, `lucide-react`.
- **States Handled:**
  - Loading: Spinning spinner and probing message.
  - Offline / Error: Full-card red alert displaying backend startup terminal command and "Retry Connection" button.
  - Online: 3-column diagnostic grid (Warehouse, LLM, Checkpoints).
- **Reusability:** **High**. Pure presentation component with event callback.

---

## 3. UI Inconsistencies & Duplication Analysis

1. **Copy-to-Clipboard Duplication:**
   - Both `ChatInterface.tsx` and `ObservabilityDashboard.tsx` implement independent `navigator.clipboard.writeText` handlers with local `setTimeout` feedback timers (2000ms).
   - *Recommendation:* Abstract into a shared `useClipboard()` hook.
2. **Table Rendering Code Duplication:**
   - Tabular data rendering logic is implemented separately in 3 different files:
     - `ChatInterface.tsx` (Data tab, lines 1018–1046)
     - `PlotlyChartRenderer.tsx` (Table fallback view, lines 181–217)
     - `SchemaReadinessSection.tsx` (Columns inspector, lines 265–354)
   - *Recommendation:* Create a reusable `<DataTable />` component supporting sorting, pagination, and empty states.
3. **Modal / Overlay Absence:**
   - No dedicated modal dialogs, drawers, or popovers currently exist. Clarification questions and honest refusals are rendered directly inline inside the message thread.
   - *Recommendation:* Introduce an accessible `<Dialog />` or `<Drawer />` system (e.g. Radix UI or headless primitives).

---
*End of Deliverable 3 (Component & Design Inventory)*

