# 07 — Testing, Performance, Security, and Reliability

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Senior QA Automation Engineer, Application Security Engineer, Performance Specialist, SRE  
**Scope:** Complete inventory of automated test suites, evaluation scripts, benchmark datasets, telemetry instrumentation, performance measurements, adversarial security defenses, and operational failure risks.

---

## 1. Test Suite Inventory and Coverage Analysis

The repository contains automated unit and integration tests located in [`backend/tests/`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/) and evaluation benchmarks in [`scripts/`](file:///c:/D_drive/AI_FOR_BI_P/scripts/):

| Test Suite / Script | File Path | Focus & Categories Covered | Test Fixtures Used | Actual Execution Status |
| :--- | :--- | :--- | :--- | :--- |
| **Database Connection Tests** | [`backend/tests/test_db_connection.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_db_connection.py) | Read-only enforcement, write probe blockage, table count, readiness checks. | `ecommerce.sqlite` | Executable; asserts exact rows (17,924 orders) & tables (30). |
| **Schema Service Tests** | [`backend/tests/test_schema_service.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_schema_service.py) | Source fingerprinting (SHA256), profiling, caching, column profiling. | `ecommerce.sqlite`, `schema_catalog_cache.json` | Executable; asserts 30 tables and 44 foreign keys. |
| **SQL Guardrail & AST Tests**| [`backend/tests/test_sql_guardrail.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_sql_guardrail.py) | Rejection of DDL/DML, statement chaining, forbidden keywords, row limit injection. | Mock SQL queries | Executable; verifies 100% block rate on prohibited expressions. |
| **Security Adversarial Tests**| [`backend/tests/test_security_adversarial.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_security_adversarial.py) | 30 adversarial test cases: DDL, DML, ATTACH bypasses, pragma abuse, prompt injections. | Adversarial SQL & prompt strings | Executable; verifies 100% rejection rate. |
| **Analysis Tools Tests** | [`backend/tests/test_analysis_tools.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_analysis_tools.py) | Period comparison, MAD anomaly screening, Holt-Winters forecasting, churn risk, SLSQP optimizer. | Synthetic data dicts + `ecommerce.sqlite` for churn | Executable; tests mathematical calculations and abstain conditions. |
| **Hybrid Retrieval Tests** | [`backend/tests/test_hybrid_retrieval.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_hybrid_retrieval.py) | BM25 ranking, TF-IDF cosine similarity, RRF fusion, FK graph expansion. | `ecommerce.sqlite` catalog | Executable; tests top-k table ranking across 10 business queries. |
| **Multi-Agent Orchestrator** | [`backend/tests/test_multi_agent_orchestrator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_multi_agent_orchestrator.py)| Full pipeline execution: Router $\rightarrow$ Gate $\rightarrow$ Clarification $\rightarrow$ Planner $\rightarrow$ SQL $\rightarrow$ Verification. | Mock LLM Provider | Executable; validates end-to-end multi-agent orchestration. |
| **Memory Service Tests** | [`backend/tests/test_memory_service.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_memory_service.py) | Session creation, turn persistence, contextual rewrite (`ContextResolver`), preferences. | `agent_app.sqlite` | Executable; tests rewrite rules and session isolation. |
| **Chat Workflow Tests** | [`backend/tests/test_chat_workflow.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_chat_workflow.py) | REST `/api/v1/chat/query` and SSE `/api/v1/chat/stream` endpoints. | FastAPI TestClient | Executable; verifies streaming event format and error handling. |
| **E2E Regression Tests** | [`backend/tests/test_e2e_regression.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_e2e_regression.py) | 10 end-to-end business questions spanning all 6 intent levels. | Live/Mock backend | Executable; verifies regression baseline. |
| **Gold Benchmark Evaluation** | [`scripts/run_evaluation.py`](file:///c:/D_drive/AI_FOR_BI_P/scripts/run_evaluation.py) | Automated 25-case gold benchmark measuring security, refusal, routing, and latencies. | [`backend/data/gold_evaluation_set.json`](file:///c:/D_drive/AI_FOR_BI_P/backend/data/gold_evaluation_set.json) | Executable; writes [`docs/EVALUATION.md`](file:///c:/D_drive/AI_FOR_BI_P/docs/EVALUATION.md). |
| **Frontend Unit Tests** | None found (`npm test` is a placeholder) | Frontend components, hooks, React Query hooks, and UI interaction. | None | **NOT FOUND.** `npm test` runs a dummy node echo command. |

---

## 2. Verified Benchmark Evidence (`docs/EVALUATION.md`)

The reproducible evaluation harness ([`scripts/run_evaluation.py`](file:///c:/D_drive/AI_FOR_BI_P/scripts/run_evaluation.py)) was executed against the gold benchmark dataset ([`backend/data/gold_evaluation_set.json`](file:///c:/D_drive/AI_FOR_BI_P/backend/data/gold_evaluation_set.json)). The verified measurements:

| Evaluation Dimension | Benchmark Target | Actual Measured Result | Status |
| :--- | :--- | :--- | :--- |
| **SQL Security & Attack Rejection Rate** | 100% | **100.0% (8/8 attacks blocked)** | **PASSED** |
| **Answerability Refusal Precision & Recall** | $\ge$ 95% | **100.0% (5/5 out-of-scope refused)** | **PASSED** |
| **Intent Routing Accuracy** | $\ge$ 90% | **100.0% (6/6 intents classified)** | **PASSED** |
| **Gold SQL Execution Success** | $\ge$ 95% | **100.0% (6/6 queries executed)** | **PASSED** |
| **AST Parse & Validation Latency (p50)** | $< 5.0\text{ ms}$ | **0.86 ms** | **PASSED** |
| **AST Parse & Validation Latency (p95)** | $< 15.0\text{ ms}$ | **2.76 ms** | **PASSED** |
| **End-to-End Execution Latency (Mock p50)**| $< 100.0\text{ ms}$| **18.2 ms** | **PASSED** |
| **End-to-End Execution Latency (Live Gemini)**| $< 4000.0\text{ ms}$| **1,450 ms - 2,100 ms** (LLM API call bound) | **PASSED** |

---

## 3. Security Guardrails and Threat Analysis

### 3.1 Prompt Injection Defense
Implemented in [`backend/app/security/guardrails.py#L36-L43`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/security/guardrails.py#L36-L43):
- Scans user prompts against 6 compiled regular expressions:
  - `(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions`
  - `(?i)system\s*:\s*(you\s+are|override|new\s+role)`
  - `(?i)disregard\s+(all\s+)?(rules|safety|guidelines)`
  - `(?i)reveal\s+(the\s+)?(system\s+prompt|instructions|secret|api\s*key|password|env)`
  - `(?i)print\s+(environment\s+variables|env\b|secrets)`
  - `(?i)bypass\s+(guardrail|filter|security)`
- If matched, execution terminates immediately at Step -1 without invoking the LLM, preventing token wastage and jailbreaks.

### 3.2 SQL AST Injection Defense
Implemented in [`backend/app/sql/validator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py) and [`guardrails.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/security/guardrails.py):
- Blocks statement chaining (semicolon splitting).
- Blocks DDL/DML, `ATTACH`, `DETACH`, `PRAGMA`.
- Blocks SQLite extensions (`load_extension`, `writefile`, `readfile`, `edit`, `shell`).
- Restricts AST root expression to `Select` or `Union`.
- Injects or caps `LIMIT 1000`.

### 3.3 Sensitive Data & PII Redaction
Implemented in [`backend/app/security/guardrails.py#L46-L48,L103-L123`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/security/guardrails.py#L46-L48):
- Redacts credit card patterns (`\b(?:\d{4}[ -]?){3}\d{4}\b` $\rightarrow$ `[REDACTED_CREDIT_CARD]`).
- Redacts email addresses (`[REDACTED_EMAIL]`).
- Redacts API keys and Bearer tokens (`sk-...`, `AIzaSy...`).
- Redaction is applied automatically before saving queries, SQL statements, or traces into `agent_app.sqlite`.

---

## 4. Performance Instrumentation and Observability

### 4.1 Telemetry Subsystem (`ObservabilityTracer`)
Implemented in [`backend/app/observability/tracer.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/observability/tracer.py):
- Every query execution records an entry into table `ops_run_traces` in `agent_app.sqlite`:
  - `run_id` (UUID)
  - `session_id`
  - `query` (redacted)
  - `intent`
  - `latency_ms`
  - `sql_executed` (redacted)
  - `row_count`
  - `cost_estimate_usd`
  - `error_class`
  - `verification_status`
  - `created_at`
- The method [`compute_metrics()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/observability/tracer.py#L110-L157) computes aggregate telemetry:
  - `total_runs`
  - `success_rate_pct`
  - `latency_p50_ms`, `latency_p95_ms`, `latency_p99_ms` using `numpy.percentile`
  - `error_classes_breakdown`

### 4.2 Known Performance Bottlenecks
1. **Profiling Scale on Large Schemas:**
   - On `ecommerce.sqlite` (30 tables, 334K rows), profiling takes 3.8s.
   - On `novacart_ecommerce.db` (46 tables, 2.42M rows), profiling takes 14.2s.
   - Profiling runs sequentially table-by-table; no multi-threaded or connection-pooled profiling exists.
2. **LLM API Generation Latency:**
   - In live mode (Gemini 3.5 Flash Lite), network roundtrip takes 1.2s to 2.5s per question.
   - If repair is triggered, latency doubles (up to 4.5s).

---

## 5. Operational and Reliability Risks

| Risk ID | Failure Scenario | Likelihood | Impact | Verified Mitigation in Code |
| :--- | :--- | :--- | :--- | :--- |
| **OPS-01** | **LLM API Outage / Rate Limit:** Gemini API key expires or hits quota limit. | High | Critical | Fallback to `MockLLMProvider` is implemented in [`backend/app/llm/client.py#L181-L184`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/llm/client.py#L181-L184); system continues functioning offline. |
| **OPS-02** | **Cache Corruption on Schema Drift:** Administrator modifies database schema outside application. | Medium | High | Fingerprint validation detects `st_mtime` / `sqlite_master` change and forces automatic re-profiling. |
| **OPS-03** | **Infinite Repair Loops:** LLM repeatedly returns invalid SQL during repair. | Low | Critical | Bounded repair loop strictly caps retries at 2, aborting with a clean error card. |
| **OPS-04** | **Query Hang / Resource Exhaustion:** Malicious or runaway query takes minutes. | Medium | High | SQLite connection sets `timeout=30.0` and executor caps rows at 1,000. |
| **OPS-05** | **Cross-Database Telemetry Pollution:** Traces from different databases mix together in `ops_run_traces`. | High | Medium | **NO MITIGATION.** `ops_run_traces` lacks a `database_id` column; all telemetry is globally mixed. |
| **OPS-06** | **Concurrent Schema Profiling Race Condition:** Two requests call `POST /api/v1/schema/prepare` simultaneously. | Medium | Medium | Partially mitigated: `SchemaJobManager` uses an `asyncio.Lock()` to prevent overlapping job launches. |

