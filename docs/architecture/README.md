# AI for BI — Enterprise Architecture Documentation Suite
## Conversational Data Scientist Agent

Welcome to the architectural specification repository for the **AI for BI — Conversational Data Scientist Agent**.

This directory contains the complete, standardized, and clutter-free architecture documentation for the project. Every diagram has been engineered to meet the rigor required for technical presentations, management reviews, enterprise architectural reviews, and academic evaluations.

---

## 1. Architectural Structure & Levels of Abstraction

The architecture is organized across standard enterprise abstraction tiers (Levels 1 through 7), complemented by a dynamic execution sequence and a cross-cutting security/observability view:

```
Level 1: System Context Diagram (01_system_context)
  │
  ├── Level 2: High-Level Application Architecture (02_high_level_application_architecture)
  │     └── Level 2 Detail: Frontend UI Architecture (02_frontend_application_architecture)
  │
  ├── Level 3: Agentic Workflow & Multi-Agent Architecture (03_agentic_workflow_architecture)
  │
  ├── Level 4: Hybrid RAG & Schema Grounding Pipeline (04_rag_schema_grounding_pipeline)
  │
  ├── Level 5: Analytical Intelligence Architecture (05_analytical_intelligence_architecture)
  │
  ├── Level 6: Database Connection & Preparation Workflow (06_database_onboarding_and_preparation)
  │
  ├── Level 7: Deployment & Infrastructure Topology (07_deployment_and_infrastructure)
  │
  ├── Dynamic View: End-to-End Business Query Execution Sequence (08_end_to_end_execution_sequence)
  │
  └── Cross-Cutting: Security, Performance & Observability Architecture (09_security_observability_architecture)
```

---

## 2. Complete Diagram Index

Each diagram is provided in standardized **`.mmd` (Mermaid Source)** format, designed for native rendering in GitHub markdown and seamless, one-click import into **Draw.io / diagrams.net**:

| Level / View | Diagram Title | Mermaid Source File | Scope & Architectural Focus |
|:---|:---|:---|:---|
| **Level 1** | System Context | [`01_system_context.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/01_system_context.mmd) | Enterprise boundary, actors (Executives, Analysts), AI for BI platform, Groq Cloud LPUs, connected warehouses. |
| **Level 2** | High-Level Application Architecture | [`02_high_level_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_high_level_application_architecture.mmd) | Complete system map decomposed into the 8 standard enterprise layers with cross-tier data flows. |
| **Level 2 (Detail)** | Frontend UI Architecture | [`02_frontend_application_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/02_frontend_application_architecture.mmd) | UI component tree, tab views (Overview, Chat, Activity, Catalog, System), SSE steppers, Plotly renderer. |
| **Level 3** | Agentic Workflow Architecture | [`03_agentic_workflow_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/03_agentic_workflow_architecture.mmd) | Agentic Supervisor, intent classification, task DAG planning, the 5 specialist agents, and verification critic. |
| **Level 4** | Hybrid RAG & Schema Grounding Pipeline | [`04_rag_schema_grounding_pipeline.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/04_rag_schema_grounding_pipeline.mmd) | FastEmbed dense vectors + BM25 lexical search, RRF ($k=60$), FK graph expander, value linking, AST security gate. |
| **Level 5** | Analytical Intelligence Architecture | [`05_analytical_intelligence_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/05_analytical_intelligence_architecture.mmd) | The 7 PRD business analytics engines (Descriptive, Diagnostic, Impact, Predictive, Scenario, Prescriptive, Critic). |
| **Level 6** | Database Onboarding & Preparation | [`06_database_onboarding_and_preparation.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/06_database_onboarding_and_preparation.mmd) | Connection onboarding, cryptographic schema fingerprinting, 7-stage asynchronous background preparation job. |
| **Level 7** | Deployment & Infrastructure | [`07_deployment_and_infrastructure.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/07_deployment_and_infrastructure.mmd) | Client tier, Node.js runtime, Uvicorn ASGI backend, local volume storage, Groq LPUs, remote database clusters. |
| **Dynamic** | End-to-End Execution Sequence | [`08_end_to_end_execution_sequence.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/08_end_to_end_execution_sequence.mmd) | Full lifecycle execution sequence from natural language query to streaming executive brief and Plotly chart. |
| **Cross-Cutting**| Security, Observability & Performance | [`09_security_observability_architecture.mmd`](file:///c:/D_drive/AI_FOR_BI_P/docs/architecture/09_security_observability_architecture.mmd) | 4-layer security boundary (Zero-trust, AST, read-only pool, redaction) and 13-stage span latency telemetry. |

---

## 3. Recommended Reading Orders

Depending on your role and evaluation objective, we recommend following these reading paths:

### A. Executive & Management Review (10-Minute High-Level Tour)
1. **Level 1 (`01_system_context`):** Understand enterprise boundaries, actors, Groq inference acceleration, and data governance.
2. **Level 2 (`02_high_level_application_architecture`):** Review how the user interface connects through security to analytical engines.
3. **Level 5 (`05_analytical_intelligence_architecture`):** Examine the business value: Impact analysis ("So What?"), scenario modeling ("What-If?"), and churn forecasting.
4. **Dynamic View (`08_end_to_end_execution_sequence`):** Walk through an executive query lifecycle.

### B. AI & Systems Architect Deep Dive
1. **Level 1 (`01_system_context`)** $\rightarrow$ **Level 2 (`02_high_level_application_architecture`)**
2. **Level 3 (`03_agentic_workflow_architecture`):** Inspect supervisor coordination, task dependency DAG generation, and specialist delegation.
3. **Level 4 (`04_rag_schema_grounding_pipeline`):** Study the dual-retrieval pipeline (FastEmbed + BM25), Reciprocal Rank Fusion, and foreign key graph expansion.
4. **Cross-Cutting (`09_security_observability_architecture`):** Verify security boundaries, AST validation (`sqlglot`), and 13-stage span telemetry.
5. **Level 7 (`07_deployment_and_infrastructure`):** Review runtime topology, local volume persistence, and Groq cloud integration.

### C. Data Science & Database Performance Engineer
1. **Level 4 (`04_rag_schema_grounding_pipeline`):** Examine schema tokenization, dense embeddings, and semantic value linking.
2. **Level 5 (`05_analytical_intelligence_architecture`):** Review the mathematical models (Holt-Winters, ARIMA, LightGBM, Student's t-test, elasticity matrix).
3. **Level 6 (`06_database_onboarding_and_preparation`):** Understand schema introspection, fingerprinting, and asynchronous background index construction.
4. **Cross-Cutting (`09_security_observability_architecture`):** Review database read-only enforcement and query latency tracking.

---

## 4. How to Open and Edit Diagrams in Draw.io

All diagrams in this directory are 100% compatible with **draw.io (diagrams.net)** and the **draw.io Desktop Application** via native Mermaid import:

1. Open any `.mmd` file in `docs/architecture/` with a text editor and copy the entire text.
2. Launch **draw.io** in your browser ([https://app.diagrams.net/](https://app.diagrams.net/)) or open the Draw.io Desktop application.
3. In Draw.io, navigate to the top menu: **Arrange $\rightarrow$ Insert $\rightarrow$ Advanced $\rightarrow$ Mermaid**.
4. Paste the Mermaid code into the modal dialog and click **Insert**.
5. Draw.io will parse the Mermaid flowchart or sequence diagram and render it with full fidelity onto the canvas for visual editing, re-styling, and export (PNG, SVG, PDF).

---

## 5. Standardized Visual Palette & Design System

The architecture diagrams use a standardized enterprise color palette to ensure immediate visual comprehension across all levels:

| Architectural Tier | Background Fill | Border Stroke | Typography Color | Visual Meaning |
|:---|:---|:---|:---|:---|
| **User Interface / Client** | `#E1F5FE` | `#0288D1` | `#01579B` | Light Blue — Client applications, presentation views, actors. |
| **API & Gateway** | `#EDE7F6` | `#5E35B1` | `#311B92` | Purple — FastAPI entry points, routers, middleware, SSE streams. |
| **Agentic Orchestration** | `#E8EAF6` | `#3949AB` | `#1A237E` | Indigo / Deep Purple — Supervisor, DAG planner, specialist agents. |
| **Intelligence & Analytics** | `#FFF3E0` | `#F57C00` | `#E65100` | Orange / Amber — Deterministic Python analytical engines, forecasting. |
| **Retrieval & Knowledge** | `#E0F2F1` | `#00897B` | `#004D40` | Teal / Cyan — FastEmbed, BM25, RRF rank fusion, schema grounding. |
| **Data & Storage** | `#E8F5E9` | `#43A047` | `#1B5E20` | Green — Relational warehouses, SQLite operational stores, indexes. |
| **External Services** | `#FCE4EC` | `#D81B60` | `#880E4F` | Pink / Crimson — Groq Cloud LPUs, external inference endpoints. |
| **Security & Observability** | `#ECEFF1` | `#546E7A` | `#263238` | Grey / Slate — AST security gates, latency tracers, audit filters. |

### Component Shape Conventions
- **Rounded Rectangles:** Software processes, agent modules, functional controllers, and UI views.
- **3D Cylinders (`[(...)]`):** Databases, vector collections, inverted lexical indexes, and persistent cache volumes.
- **Diamonds / Rhombuses (`{...}`):** Decision gates, conditional logic, and AST validation branches.
- **Grouped Swimlanes:** Architectural tiers, execution stages, and container boundaries.

---

## 6. Core Architectural Invariants

Every diagram reflects four non-negotiable architectural principles implemented in the source code:

1. **Separation of Reasoning and Computation:**
   - LLMs (Groq Cloud API) perform **only** semantic understanding, SQL translation, and narrative synthesis.
   - All calculations, forecasts, statistical tests, and optimizations are computed exclusively by **deterministic Python code** (NumPy, Pandas, SciPy, statsmodels, LightGBM). Hallucinated calculations are mathematically impossible.
2. **Strict Read-Only Data Governance:**
   - Database connections run under read-only transaction parameters.
   - Every generated SQL statement passes through a `sqlglot` AST security gate that immediately aborts if any non-`SELECT` statement (`INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, `TRUNCATE`) or multi-statement injection is detected.
3. **Domain-Independent Schema Grounding:**
   - Zero hardcoded business assumptions. The agent operates across healthcare, retail, logistics, SaaS, and financial schemas via dynamic introspection, FastEmbed dense vector embeddings, and persistent BM25 lexical ranking.
4. **Exclusive Groq Cloud Inference:**
   - Optimized exclusively for ultra-low-latency Groq Cloud LPUs running `llama-3.3-70b-versatile` and `openai/gpt-oss-120b`. Legacy multi-provider fallbacks have been purged from production.

