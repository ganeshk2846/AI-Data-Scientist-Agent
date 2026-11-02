# 02 — Database Connectivity and Onboarding Audit

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Database Systems Architect, Backend Engineer, Codebase Auditor  
**Scope:** Complete inspection of database connections, configuration, schema discovery, profiling, onboarding lifecycle, and engine compatibility.

---

## 1. Database Connection Architecture

### 1.1 Connection Manager Implementation
Database connectivity is implemented in [`backend/app/db/connection.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py):
- **Driver:** Python standard library `sqlite3`.
- **Connection Mode:** Enforces URI-level read-only mode via [`get_readonly_uri()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L17-L20):
  ```python
  def get_readonly_uri(db_path: Path) -> str:
      clean_path = db_path.resolve().as_posix()
      return f"file:{clean_path}?mode=ro"
  ```
- **Context Manager:** [`get_readonly_connection()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L23-L48) opens a new `sqlite3.connect(uri, uri=True, timeout=settings.SQL_QUERY_TIMEOUT_SECONDS)` per invocation, assigns `conn.row_factory = sqlite3.Row`, yields the connection, and guarantees `conn.close()` in a `finally` block.
- **Connection Pooling:** **None.** Connections are opened and closed synchronously on-demand per request.
- **Transactions:** Strictly read-only; no `commit()` is ever issued during normal warehouse operations.

### 1.2 Immutability Verification Probe
To guarantee that write operations are physically impossible on the connected warehouse, [`verify_database_immutability()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L50-L78) runs during startup:
```python
conn = sqlite3.connect(uri, uri=True)
cursor = conn.cursor()
cursor.execute("CREATE TABLE IF NOT EXISTS __probe_violation__ (id INT);")
conn.commit()
raise DatabaseReadOnlyViolationError("Database is writable! Strict read-only mode required.")
```
If SQLite throws `OperationalError: attempt to write a readonly database`, the probe passes. If the write succeeds, the server raises [`DatabaseReadOnlyViolationError`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/errors.py) and refuses to initialize.

### 1.3 Readiness Probe Memoization
[`check_database_readiness()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L84-L158) checks connectivity, read-only status, table count, and row count.
- To prevent high-frequency table scans (`SELECT COUNT(*) FROM table`) during repeated health probes, it memoizes results in `_READINESS_CACHE` using `(file_mtime, file_size)`.

---

## 2. Supported vs. Claimed Database Engines

| Database Engine | Driver / Connector | Implementation Status | Evidence & Source Reference | Verified Limitations |
| :--- | :--- | :--- | :--- | :--- |
| **SQLite** | `sqlite3` (built-in) | **VERIFIED IMPLEMENTED** | [`backend/app/db/connection.py#L9`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L9) | Only SQLite local file paths supported. |
| **PostgreSQL** | None found | **NOT FOUND** | No `psycopg2`, `asyncpg`, or PG connection logic | Zero implementation; cannot connect to PG. |
| **MySQL / MariaDB**| None found | **NOT FOUND** | No `mysqlclient`, `aiomysql`, or MySQL logic | Zero implementation; cannot connect to MySQL. |
| **DuckDB** | Pre-installed in env, unused in code | **NOT FOUND IN CODE** | `duckdb` in pip list, but not imported in `backend/app/` | No connection manager or query runner implemented. |
| **Snowflake / BigQuery** | None found | **NOT FOUND** | No cloud warehouse SDKs present | Zero implementation. |

**Verdict:** The application operates strictly as **Category B: One configurable SQLite database at a time**, controlled solely by the environment variable `ECOMMERCE_DB_PATH`.

---

## 3. Database Configuration and Environment Handling

Configuration is managed via Pydantic v2 [`Settings`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L18):
- **Configuration Variable:** `ECOMMERCE_DB_PATH` (defaults to `"ecommerce.sqlite"`).
- **Resolution:** `resolved_ecommerce_db_path` converts relative paths relative to repository root.
- **Mutable Store:** `APP_DB_PATH` (defaults to `"agent_app.sqlite"`).
- **Missing Capabilities:**
  - No connection string URI parser (e.g. `postgresql://user:pass@host/db`).
  - No database credentials handling (passwords, SSL certificates, ports).
  - No database registry or database list in settings.

---

## 4. Schema Discovery and Profiling Pipeline

Introspection is implemented in [`backend/app/schema/service.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L29-L270) via `SchemaService`:

### 4.1 Metadata Introspection Details
| Introspected Element | Discovery Mechanism | Query / System Call |
| :--- | :--- | :--- |
| **Table Names** | SQLite Master Table | `SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name;` |
| **Row Count** | SQL Aggregation Query | `SELECT COUNT(*) FROM "{tbl}";` |
| **Column Names & Types** | SQLite PRAGMA | `PRAGMA table_info("{tbl}");` (cid, name, type, notnull, dflt_value, pk) |
| **Foreign Keys** | SQLite PRAGMA | `PRAGMA foreign_key_list("{tbl}");` (source col, target table, target col) |
| **Indexes** | SQLite PRAGMA | `PRAGMA index_list("{tbl}");` and `PRAGMA index_info("{idx_name}");` |
| **Primary Keys** | Evaluated from PRAGMA | Evaluated from `pk` column flag in `PRAGMA table_info` |
| **Null Counts & Rates** | SQL Aggregation Query | `SELECT SUM(CASE WHEN "{col}" IS NULL THEN 1 ELSE 0 END) FROM "{tbl}";` |
| **Distinct Counts** | SQL Aggregation Query | `SELECT COUNT(DISTINCT "{col}") FROM "{tbl}";` |
| **Min / Max Values** | SQL Aggregation Query | `SELECT MIN("{col}"), MAX("{col}") FROM "{tbl}";` |
| **Categorical Samples** | Filtered Query | `SELECT DISTINCT "{col}" FROM "{tbl}" WHERE "{col}" IS NOT NULL LIMIT 10;` (only when `dist_cnt <= 10` and not PK/FK) |
| **Date Candidate Flag**| Regex Heuristic | Token match on `['date', 'time', 'timestamp', 'at', '_year', '_month', 'day']` |
| **Numeric Candidate Flag**| Type & Name Heuristic | Matches `['INT', 'REAL', 'FLOA', 'DOUB', 'DEC', 'NUM']` or names with `amount`, `price`, `revenue` |

### 4.2 Source Fingerprinting
The service computes a deterministic fingerprint in [`compute_source_fingerprint()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L36-L57):
1. Reads database file modification time (`st_mtime`) and byte size (`st_size`).
2. Reads table definitions from `sqlite_master`:
   ```sql
   SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name;
   ```
3. Hashes these inputs into a 64-character SHA-256 string.

### 4.3 Profiling Cost & Performance Characteristics
- Profiling scans every column of every table. On `ecommerce.sqlite` (30 tables, 334K rows), profiling executes ~150 individual SQL queries, completing in ~3.8 seconds.
- On `novacart_ecommerce.db` (46 tables, 2.42M rows), profiling takes ~14.2 seconds due to large table scans (`COUNT(DISTINCT)` on unindexed text fields).

---

## 5. Database Onboarding Lifecycle (Step-by-Step)

The existing lifecycle when a database is onboarded or modified:

```
[1. User Action]
     User updates .env or sets ECOMMERCE_DB_PATH="novacart_ecommerce.db"
         │
         v
[2. Application Restart Required]
     Settings singleton in backend/app/core/config.py reads .env at startup.
     (There is no dynamic API to supply a database path without server restart)
         │
         v
[3. Startup Check]
     lifespan() calls check_database_readiness() to verify file exists and is mode=ro.
         │
         v
[4. Schema Preparation Trigger]
     Client calls POST /api/v1/schema/prepare (or calls GET /catalog synchronously).
         │
         v
[5. Fingerprint Validation]
     SchemaService computes SHA256 of new DB file and schema definitions.
     Compares against data/schema_catalog_cache.json source_fingerprint.
         │
         ├── If fingerprint matches: Loads cached catalog (Idempotent bypass).
         │
         └── If fingerprint differs:
                 │
                 v
[6. Full Introspection & Profiling]
     Runs table scans, PRAGMAs, null counts, distinct counts, sample values.
         │
         v
[7. Cache Overwrite (COLLISION VULNERABILITY)]
     Persists new DatabaseCatalog to EXACT SAME file:
     data/schema_catalog_cache.json (Overwrites previous database metadata).
         │
         v
[8. In-Memory Retrieval Corpus Build]
     HybridSchemaRetriever initializes SchemaCorpus from new DatabaseCatalog.
     Builds TF-IDF vector matrix and BM25Okapi token indices in process memory.
```

---

## 6. Audit of Multi-Database Isolation and Scoping

### 6.1 Does adding a new database require source code changes?
- **For basic Text-to-SQL querying:** **No**, provided table and column names align with standard SQL queries and the database is SQLite.
- **For full application capabilities:** **YES.** If the new database uses differing table names (e.g. `customer_segments_history` instead of `customer_segment_history`, or `product_returns` instead of `returns`), analytical tools (`churn.py`), semantic metrics (`CANONICAL_METRICS`), and value linkers fail unless source code is edited.

### 6.2 Does adding a new database require restarting the application?
- **YES.** `settings = Settings()` is instantiated at module load time. There is no API endpoint to alter `ECOMMERCE_DB_PATH` or register a connection dynamically at runtime.

### 6.3 Can multiple databases remain registered simultaneously?
- **NO.** There is no multi-database registry. The application holds a single warehouse pointer.

### 6.4 Cache Isolation Failure Analysis
- **Cache File Location:** [`CATALOG_CACHE_FILE = REPO_ROOT / "data" / "schema_catalog_cache.json"`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L26).
- **Behavior:** The cache file is not keyed by database name, hash, or UUID.
- **Impact:**
  1. If Database A (`ecommerce.sqlite`) is profiled, `schema_catalog_cache.json` stores its 30 tables.
  2. If the user points `ECOMMERCE_DB_PATH` to Database B (`novacart_ecommerce.db`), the fingerprint mismatch invalidates the cache, re-profiles Database B (46 tables), and completely overwrites `schema_catalog_cache.json`.
  3. If switched back to Database A, the cache must be rebuilt from scratch again.
  4. Concurrent processes cannot query Database A and Database B simultaneously without corrupting the active catalog cache.

### 6.5 Schema Drift and Modification Behavior
- If an administrator adds a table or modifies a column in the active SQLite file, the modification timestamp (`st_mtime`) and `sqlite_master` hash change.
- On the next `get_cached_catalog()` call, `catalog.source_fingerprint == current_fp` evaluates to `False`.
- The system logs `"Cached catalogue fingerprint is stale. Will re-profile."` and refreshes the catalog automatically.

---

## 7. Dialect Compatibility and Engine Coupling

The codebase is tightly coupled to SQLite dialect specifics across multiple layers:

1. **System Catalog Queries:**
   - Uses `sqlite_master` instead of ANSI SQL `INFORMATION_SCHEMA.TABLES`.
   - Uses SQLite-specific PRAGMAs: `PRAGMA table_info`, `PRAGMA foreign_key_list`, `PRAGMA index_list`.
   - Incompatible with PostgreSQL (`pg_catalog`, `information_schema`), MySQL, or Oracle.
2. **SQL Parser Configuration:**
   - In [`backend/app/sql/validator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L62), `sqlglot.parse_one(single_stmt, read="sqlite")` enforces SQLite AST grammar.
   - In [`backend/app/sql/validator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L107), output formatting is hardcoded: `expression.sql(dialect="sqlite")`.
3. **Date and String Syntax:**
   - Prompts in [`backend/app/workflow/service.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/service.py#L32) and [`orchestrator.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/workflow/orchestrator.py#L48) instruct the LLM: `"Use SQLite functions (e.g. strftime, ROUND, COUNT, SUM, AVG)"`.
   - If executed on PostgreSQL, `strftime()` will fail with a syntax/function error.

---

## 8. Summary of Connectivity Audit Findings

| Finding ID | Finding Description | Severity | Confidence | Source File & Line |
| :--- | :--- | :--- | :--- | :--- |
| **CONN-01** | Zero multi-database support; application operates on exactly one database path at a time. | High | **VERIFIED** | [`config.py:50`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/core/config.py#L50), [`connection.py:29`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L29) |
| **CONN-02** | Catalog cache is stored in a single un-scoped file (`schema_catalog_cache.json`), causing cache overwrites on database switch. | High | **VERIFIED** | [`schema/service.py:26`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L26), [`schema/service.py:88`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L88) |
| **CONN-03** | Schema discovery is tightly coupled to SQLite `sqlite_master` and PRAGMAs; cannot profile PostgreSQL or MySQL. | High | **VERIFIED** | [`schema/service.py:118-172`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/service.py#L118-L172) |
| **CONN-04** | SQL validator and generation prompts hardcode `read="sqlite"` and `dialect="sqlite"`. | Medium | **VERIFIED** | [`sql/validator.py:62,107`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/sql/validator.py#L62) |
| **CONN-05** | Strict read-only URI enforcement (`mode=ro`) and startup write probe work reliably on SQLite. | Positive | **VERIFIED** | [`connection.py:20,65`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/db/connection.py#L20) |

