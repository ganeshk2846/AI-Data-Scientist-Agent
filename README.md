# AI-Powered Data Scientist Agent for Business Intelligence (AI for BI)

An enterprise-grade, conversational Data Scientist and Business Intelligence agent built on top of a multi-domain SQLite warehouse (`ecommerce.sqlite`). The system enables business users to ask natural-language business questions across six analytical levels (**What, Why, So What, What Next, What If, Now What**), retrieves the verified database schema, generates and validates safe read-only SQL, executes deterministic statistical and ML analysis, renders interactive visualizations, and composes business-oriented narratives with strict evidence traceability.

---

## 1. Architectural Pipeline & Design Principles

The runtime follows a strict pipeline:
$$\text{Retrieve} \longrightarrow \text{Constrain} \longrightarrow \text{Plan} \longrightarrow \text{Generate} \longrightarrow \text{Validate} \longrightarrow \text{Execute} \longrightarrow \text{Verify} \longrightarrow \text{Analyze} \longrightarrow \text{Visualize} \longrightarrow \text{Explain}$$

### Core Operating Principles
1. **LLM for Language, Code for Numbers:** LLMs classify intents, ground queries, generate schema-constrained SQL, and narrate findings. All arithmetic, trend calculations, forecasting, and statistical modeling run in deterministic, tested Python tools.
2. **Strictly Read-Only Business Warehouse:** `ecommerce.sqlite` is treated as immutable and opened with `mode=ro`. The agent never alters, writes to, migrates, or creates tables in the source database.
3. **Agent-Owned Local Store:** Checkpoints, session state, audit traces, and precomputed insights reside exclusively in a separate, writable agent-owned SQLite database (`agent_app.sqlite`).
4. **AST-Enforced SQL Guardrails:** SQL generation is restricted strictly to retrieved schema identifiers. Queries are parsed and validated via `sqlglot` to reject mutations, DDL, PRAGMA alterations, multi-statement injection, and unindexed full-table scans.
5. **No Redis / No Complex Container Swarms:** Clean, in-process asynchronous task scheduling and LangGraph local SQLite checkpointers provide high performance and low operational complexity for development and testing.

---

## 2. Technology Stack

- **Backend API:** Python 3.14+, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings
- **Workflow Orchestration:** LangGraph (stateful graph orchestration with local checkpoints)
- **Database Access & Safety:** SQLite (`mode=ro`), SQLAlchemy 2.x (for agent-owned store), `sqlglot` (SQL AST parser/validator)
- **Schema Grounding & Retrieval:** BM25 (`rank-bm25`) lexical search + local embedding retrieval with Reciprocal Rank Fusion (RRF)
- **Analysis Engine:** `pandas`, `statsmodels`, `scikit-learn`, `scipy`, `xgboost`
- **Frontend Application:** Next.js (App Router), React, TypeScript, Tailwind CSS, shadcn/ui, TanStack Query
- **Contract Validation:** Pydantic v2 (backend) and Zod (frontend)
- **Visualizations:** Plotly.js (with full tabular and text fallback)
- **Streaming:** Server-Sent Events (SSE) via `sse-starlette`
- **Testing:** `pytest` (backend)

---

## 3. Verified Dataset Overview (`ecommerce.sqlite`)

The provided business warehouse has been fully profiled and validated in Phase 0:
- **Total Tables:** 30 interconnected tables
- **Total Views:** 0
- **Total Rows:** 334,503 rows across all tables
- **Total Indexes:** 61 indexes
- **Foreign Key Declarations:** 44 foreign key relationships (0 violations verified via `PRAGMA foreign_key_check`)
- **Temporal Span:** January 1, 2023 to December 31, 2025 (3 complete calendar years; 1,096 consecutive days)
- **Financial Baseline:** 17,924 orders totaling \$21,761,969.17 gross (\$20,891,624.33 delivered across 17,274 orders; \$870,344.84 cancelled across 650 orders).

For the complete schema inventory, column data types, null rates, and anomaly observations, refer to [DATASET_PROFILE.md](docs/DATASET_PROFILE.md).

---

## 4. Repository Layout

```text
AI_FOR_BI_P/
├── .env.example                      # Template configuration with safe placeholders
├── .gitignore                         # Comprehensive ignore rules (secrets, venvs, caches, sqlite)
├── README.md                          # Architecture, setup, run, test, and troubleshooting guide
├── DEVELOPMENT_HISTORY.md             # Mandatory chronological audit trail
├── PromptforAICodingTool.md           # Engineering guidelines and phase plan
├── DataScientistAgentArchitecture_final.md # Architectural design reference specification
├── ecommerce.sqlite                   # Source business dataset (strictly read-only)
├── docs/
│   ├── DATASET_PROFILE.md             # Verified inventory of all 30 tables, schemas, and metrics
│   ├── ARCHITECTURE.md                # Implemented architecture & component boundaries
│   └── EVALUATION.md                  # Metric definitions and gold test cases (Phase 9/10)
├── scripts/
│   ├── inspect_db.py                  # Read-only database inspection script
│   ├── audit_quality.py               # Data quality, FK constraint, and PK uniqueness auditor
│   └── generate_dataset_profile.py   # Dataset profile documentation generator
├── backend/                           # FastAPI backend (Phase 1+)
└── frontend/                          # Next.js App Router frontend (Phase 1+)
```

---

## 5. Getting Started & Verification

### Prerequisites
- **Python:** 3.11+ (tested on Python 3.14.7)
- **Node.js:** v20+ (tested on Node v24.20.0, npm 11.19.0)
- **Git:** 2.40+ (tested on git version 2.51.1)

### Environment Configuration
Copy the template environment file:
```bash
cp .env.example .env
```
*(Configure optional LLM provider keys in `.env` if natural-language synthesis is enabled; the application boots cleanly in mock/offline mode without API keys).*

### Running Database Reconnaissance
To verify read-only database connectivity and generate the dataset profile:
```bash
# Verify read-only access and generate raw inspection JSON
python scripts/inspect_db.py

# Audit foreign key integrity and data quality
python scripts/audit_quality.py

# Re-generate the markdown profile document
python scripts/generate_dataset_profile.py
```

---

## 6. Implementation Roadmap & Phase Gate Status

| Phase | Description | Status | Completion Date | Reference |
|---|---|---|---|---|
| **Phase 0** | Repository & Dataset Reconnaissance | **Complete** | 2026-11-01 | [DATASET_PROFILE.md](docs/DATASET_PROFILE.md) |
| **Phase 1** | Project Foundation & Developer Experience | Pending | - | - |
| **Phase 2** | Read-Only DB Connection & Schema Preparation | Pending | - | - |
| **Phase 3** | Natural-Language Question API & First Vertical Slice | Pending | - | - |
| **Phase 4** | Multi-Agent Workflow, Planning & Bounded Repair | Pending | - | - |
| **Phase 5** | Hybrid Schema Retrieval & Business Semantics | Pending | - | - |
| **Phase 6** | Deterministic Analysis Tools (Descriptive, Predictive) | Pending | - | - |
| **Phase 7** | Visualization & Business Answer Composition | Pending | - | - |
| **Phase 8** | Shared Memory Service & Reusable Knowledge | Pending | - | - |
| **Phase 9** | Security, Observability & Evaluation | Pending | - | - |
| **Phase 10** | End-to-End Validation & Final Documentation | Pending | - | - |

See [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md) for detailed execution history, command outcomes, and design decisions.
