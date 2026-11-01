# Development History & Audit Trail

## Project Status Matrix

| Phase | Title | Status | Completion Date | Milestone / Deliverables |
|---|---|---|---|---|
| **Phase 0** | Repository and dataset reconnaissance | **Complete** | 2026-11-01 | [DATASET_PROFILE.md](docs/DATASET_PROFILE.md), `scripts/inspect_db.py`, `.gitignore`, `README.md` |
| **Phase 1** | Project foundation and developer experience | Pending | - | FastAPI & Next.js skeletons, health endpoints, test harness |
| **Phase 2** | Read-only database connection & schema preparation | Pending | - | DB manager, metadata catalogue, async preparation job |
| **Phase 3** | NL question API & first reliable vertical slice | Pending | - | Chat endpoint, schema retriever, SQL validator, runner |
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
  - Phase 1 — Project foundation and developer experience: Scaffolding FastAPI backend, Next.js frontend, Pydantic configuration, health/readiness endpoints, structured error models, and initial automated test harness.
