# AI-Powered Data Scientist Agent for Business Intelligence (AI for BI)

An enterprise-grade, conversational Data Scientist and Business Intelligence agent built against a multi-domain SQLite data warehouse (`ecommerce.sqlite`). The system enables business stakeholders to ask natural-language questions across six analytical levels (**What, Why, So What, What Next, What If, Now What**), retrieves the verified database schema, generates and validates safe read-only SQL, executes deterministic statistical and ML calculations, renders interactive Plotly visualizations, and composes business narratives with strict evidence traceability.

---

## 1. System Architecture & Pipeline

```
User Question ──► ContextResolver ──► Router Agent ──► Answerability Gate ──► Clarification
                        │
                        ▼
Planner DAG (7 Steps) ──► Hybrid Retriever (BM25 + TF-IDF RRF + FK Graph + Value Linker)
                        │
                        ▼
SQL Generator ──► AST Security Guardrail ──► Bounded Repair (2x) ──► Read-Only Executor
                        │
                        ▼
Deterministic Python Tools (Anomalies, Forecasts, Churn, Optimization)
                        │
                        ▼
Visualization Agent (Plotly.js) ──► Executive Composer ──► Telemetry Tracer (p50/p95)
```

For detailed architectural specifications and design decisions, refer to [ARCHITECTURE.md](docs/ARCHITECTURE.md).

---

## 2. Implementation Status & Phase Roadmap

All 10 project phases have been completed, verified with actual executed code, merged into `main` via `--no-ff`, and tagged:

| Phase | Milestone | Git Tag | Status | Documentation / Deliverables |
|---|---|---|---|---|
| **Phase 0** | Repository & Dataset Reconnaissance | `phase-0-complete` | **Complete** | [DATASET_PROFILE.md](docs/DATASET_PROFILE.md), `scripts/inspect_db.py`, `.gitignore` |
| **Phase 1** | Project Foundation & Dev Experience | `phase-1-complete` | **Complete** | FastAPI, Next.js 14, Pydantic/Zod contracts, health harness |
| **Phase 2** | Schema Preparation & Profiling | `phase-2-complete` | **Complete** | Schema catalogue, SHA-256 fingerprint caching, catalog browser UI |
| **Phase 3** | NL Query API & Vertical Slice | `phase-3-complete` | **Complete** | Router, Grounder, `sqlglot` guardrail, vertical slice chat UI |
| **Phase 4** | Multi-Agent Planning & Bounded Repair | `phase-4-complete` | **Complete** | Planner DAG, Answerability Gate, Clarification, Bounded 2-attempt Repair |
| **Phase 5** | Hybrid Schema Retrieval & Semantics | `phase-5-complete` | **Complete** | BM25 + embedding RRF ($k=60$), FK graph expansion, value linker, metrics |
| **Phase 6** | Reliable Analysis Tools | `phase-6-complete` | **Complete** | Deterministic stats, MAD anomalies, trend forecast, churn risk, SLSQP optimizer |
| **Phase 7** | Visualization & Business Composition | `phase-7-complete` | **Complete** | Plotly.js chart renderer, table fallbacks, analytical follow-up suggestions |
| **Phase 8** | Shared Memory & Reusable Knowledge | `phase-8-complete` | **Complete** | Central `MemoryService`, ContextResolver, `agent_app.sqlite`, session controls |
| **Phase 9** | Security, Observability & Evaluation | `phase-9-complete` | **Complete** | AST injection defenses, 100% benchmark score, telemetry traces, [EVALUATION.md](docs/EVALUATION.md) |
| **Phase 10** | End-to-End Validation & Final Sign-Off | `phase-10-complete` | **Complete** | 114 backend tests passing, Next.js production build, developer docs |

For the chronological implementation log, refer to [DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md).

---

## 3. Technology Stack

- **Backend API:** Python 3.14+, FastAPI, Uvicorn, Pydantic v2, Pydantic-Settings
- **Database Access & Safety:** SQLite (`mode=ro`), `sqlglot` (SQL AST parser/validator)
- **Schema Grounding & Retrieval:** BM25 (`rank-bm25`) + local TF-IDF cosine similarity with Reciprocal Rank Fusion (RRF, $k=60$)
- **Analysis Engine:** `pandas`, `statsmodels`, `scipy.optimize` (SLSQP), `scikit-learn`
- **Application Store:** Local SQLite (`agent_app.sqlite` for sessions, active frames, preferences, and telemetry)
- **Frontend Application:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Lucide Icons, TanStack Query
- **Visualization:** `plotly.js-dist-min` (interactive charts with automatic table fallback)
- **Streaming:** Server-Sent Events (SSE) via `sse-starlette`
- **Testing:** `pytest` (114 passing backend unit and integration tests)

---

## 4. Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.14.7)
- Node.js 18+ (tested on Node v24.20.0) & npm 10+
- The `ecommerce.sqlite` database file located in the project root

### Environment Configuration
Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```
Default configuration runs out-of-the-box in `MockLLMProvider` mode (no external API keys required). If using Google Gemini, set:
```env
LLM_PROVIDER=gemini
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.0-flash
```

### Running the Python Backend
```bash
# From repository root:
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```
- API Documentation (Swagger): `http://localhost:8000/docs`
- Alternative API Documentation (ReDoc): `http://localhost:8000/redoc`
- Readiness Health Check: `http://localhost:8000/api/v1/ready`

### Running the Next.js Frontend
```bash
cd frontend
npm install
npm run dev
```
Open `http://localhost:3001` in your web browser (defaulted to port 3001 to avoid conflicts on 3000; or pass any port with `npx next dev -p <port>`).

---

## 5. Verification & Testing

### 1. Run Complete Backend Test Suite
```bash
python -m pytest backend/tests -v
```
*Current test status: 114 passed in ~3.5 seconds.*

### 2. Run Reproducible Evaluation Harness
```bash
python scripts/run_evaluation.py
```
*Evaluates 25 gold benchmark test cases grounded in `ecommerce.sqlite`, verifying 100% security rejection, 100% refusal precision, and sub-15ms validation latencies.*

### 3. Build Production Frontend Bundle
```bash
cd frontend
npm run build
```
*Verifies TypeScript type safety, static page generation, and Plotly bundle compilation.*

---

## 6. Key Documentation Reference

- **[DATASET_PROFILE.md](docs/DATASET_PROFILE.md):** Complete schema profile, foreign key inventory, null rates, and financial metrics across all 30 tables and 334,503 rows.
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md):** Multi-agent orchestration, hybrid retrieval, bounded repair, deterministic analysis tools, and telemetry design.
- **[EVALUATION.md](docs/EVALUATION.md):** Benchmark results, naive baseline comparison, latency percentiles, and security verification.
- **[DEVELOPMENT_HISTORY.md](DEVELOPMENT_HISTORY.md):** Complete chronological audit log of all 10 phases.
