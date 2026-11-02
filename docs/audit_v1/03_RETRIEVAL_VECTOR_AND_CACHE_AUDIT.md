# 03 — Retrieval, Vector, and Cache Audit

**Target System:** AI for BI Data Scientist Agent (v0.1.0)  
**Audit Date:** 2026-11-02  
**Auditor Roles:** Senior RAG and Retrieval Engineer, Machine Learning Engineer, Codebase Auditor  
**Scope:** Complete verification of vector retrieval, embedding models, BM25 lexical ranking, Reciprocal Rank Fusion, metadata corpus construction, entity linking, and per-database cache scoping.

---

## 1. Vector Database vs. Vector Retrieval Reality

### 1.1 Direct Answer to the Core Question
**Does the project use an external or embedded Vector Database (such as Pinecone, ChromaDB, Qdrant, Weaviate, Milvus, LanceDB, pgvector, or FAISS)?**

**VERIFIED ANSWER:** **NO. No dedicated vector database exists anywhere in this project.**
- There are no dependencies for Chroma, Qdrant, Weaviate, Milvus, LanceDB, or FAISS in [`backend/requirements.txt`](file:///c:/D_drive/AI_FOR_BI_P/backend/requirements.txt) or [`backend/pyproject.toml`](file:///c:/D_drive/AI_FOR_BI_P/backend/pyproject.toml).
- There is no external vector microservice, Docker container, or cloud embedding API integration.

### 1.2 What Does the System Actually Use?
The project uses an **in-memory, local TF-IDF sparse vector space model with cosine similarity**, implemented directly using `scikit-learn`:
- **Class:** [`LocalTFIDFEmbeddingRetriever`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py#L19-L44)
- **Source File:** [`backend/app/retrieval/embeddings.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py)
- **Vector Algorithm:** `TfidfVectorizer(stop_words="english", ngram_range=(1, 2), sublinear_tf=True)`
- **Similarity Metric:** `sklearn.metrics.pairwise.cosine_similarity`
- **Official Class Docstring:**
  > *"Local semantic retriever based on TF-IDF vector space cosine similarity. Provides fast, deterministic semantic ranking without requiring external vector DBs or cloud APIs."*

---

## 2. Complete Schema Retrieval Architecture

The retrieval engine matches the user's natural language question against schema tables and foreign key relationships using a 4-stage hybrid pipeline:

```
[ User Query ]
       │
       ├─────────────────────────────────┬─────────────────────────────────┐
       │                                 │                                 │
       v                                 v                                 v
[ Stage 1: Lexical BM25 ]      [ Stage 2: Dense TF-IDF ]        [ Stage 3: Entity Value Linker ]
  BM25Retriever                  LocalTFIDFEmbeddingRetriever     ValueLinker
  (rank_bm25 / BM25Okapi)        (scikit-learn cosine sim)        (Regex literal entity matcher)
  Scores exact term matches      Scores semantic n-gram overlap   Extracts target table/col pairs
       │                                 │                                 │
       └────────────────┬────────────────┘                                 │
                        │                                                  │
                        v                                                  │
       [ Stage 4: Reciprocal Rank Fusion (RRF) ]                           │
         RRF_K = 60                                                        │
         score = 1/(60 + r_bm25) + 1/(60 + r_embed)                        │
         Selects Top-5 Candidate Tables                                    │
                        │                                                  │
                        v                                                  │
       [ Stage 5: FK Graph Expansion ]                                     │
         Inspects 1-hop foreign key outgoing links                         │
         Appends join partner tables (capped at 7)                         │
                        │                                                  │
                        └────────────────────────┬─────────────────────────┘
                                                 │
                                                 v
                                  [ Minimal Schema Prompt ]
                                  (Supplied to LLM Context)
```

---

## 3. Detailed Component Breakdown

### 3.1 Metadata Document Construction (`SchemaCorpus`)
Implemented in [`backend/app/retrieval/corpus.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L71-L124):
- For each table in the active [`DatabaseCatalog`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/schema/models.py#L65), `SchemaCorpus` constructs a [`TableDocument`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L45-L55):
  - **Table Name** (e.g. `orders`)
  - **Domain Description:** Sourced from [`DOMAIN_DESCRIPTIONS`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L11-L42). If table is not in the dictionary, defaults to `"General Operational Data"`.
  - **Column Names & Roles:** Marks columns with heuristic roles: `"primary key"`, `"foreign key referencing X.Y"`, `"date timestamp calendar"`, `"numeric metric amount money"`.
  - **Foreign Key Links:** Textual representation of FK edges.
  - **Sample Categorical Values:** Safe sample literals from low-cardinality columns.
  - **Composite Search Text:** Formatted multi-line document combining all the above.
- **Tokenization:** [`tokenize_text()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L57-L68) extracts regex word tokens `\b[a-zA-Z0-9_]{2,}\b` and expands `snake_case` tokens into individual word components.

### 3.2 Lexical Retrieval (`BM25Retriever`)
Implemented in [`backend/app/retrieval/bm25.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/bm25.py):
- Uses `BM25Okapi` from the `rank-bm25` library.
- Initialized with tokenized documents across all tables.
- Returns list of `(table_name, score)` pairs sorted descending by score.

### 3.3 Semantic Retrieval (`LocalTFIDFEmbeddingRetriever`)
Implemented in [`backend/app/retrieval/embeddings.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/embeddings.py):
- Fits `TfidfVectorizer` over all document search texts in the corpus.
- Transforms incoming natural language query into vector space.
- Calculates `cosine_similarity(query_vec, doc_matrix)`.
- Returns top-K scored tables.

### 3.4 Hybrid Fusion with Reciprocal Rank Fusion (RRF)
Implemented in [`backend/app/retrieval/hybrid.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L45-L83):
- **Constant:** `RRF_K = 60` (standard IR benchmark constant).
- **Formula:**
  $$\text{RRF Score}(t) = \frac{1}{60 + \text{Rank}_{\text{BM25}}(t)} + \frac{1}{60 + \text{Rank}_{\text{Embedding}}(t)}$$
- Missing tables in either rank list default to rank `100`.
- Selects top 5 initial tables.

### 3.5 Foreign Key Graph Expansion
Implemented in [`backend/app/retrieval/hybrid.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L84-L113):
- For each table in the top-5 set, inspects its outgoing foreign keys.
- If the foreign key target table is not yet in the set and shares query tokens or if total tables < 4, it expands the join set by adding the target table (capped at `max_expanded = 7`).
- Assigns `is_expanded_join = True` and records `expansion_reason` (e.g. `"Foreign key join link: order_items.product_id -> products.product_id"`).

### 3.6 Categorical Entity Linking (`ValueLinker`)
Implemented in [`backend/app/retrieval/value_linker.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/value_linker.py):
- Scans user query against regex patterns to link colloquial terms to database literals:
  - `"vip"` $\rightarrow$ `customer_segments.segment_name = 'VIP'`
  - `"delivered"` $\rightarrow$ `orders.order_status = 'delivered'`
  - `"credit card"` $\rightarrow$ `payments.payment_method = 'credit_card'`
  - `"black friday"` $\rightarrow$ `promotions.promotion_name = 'Black Friday 2024'`
  - `"paid search"` $\rightarrow$ `marketing_channels.channel_name = 'Paid Search'`
- Injects exact SQL filter recommendations directly into the LLM prompt.

---

## 4. Index Persistence, Lifecycle, and Invalidation

### 4.1 In-Memory Ephemeral Lifecycle
- **Storage:** Retrieval indexes (both BM25 token lists and TF-IDF sparse matrices) are **ephemeral in-process Python objects**.
- **Persistence:** **None.** Indexes are never saved to disk.
- **Initialization:** Built on-the-fly when [`HybridSchemaRetriever`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L36) is instantiated:
  ```python
  self.catalog = catalog or schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
  self.corpus = SchemaCorpus(self.catalog)
  self.bm25 = BM25Retriever(self.corpus)
  self.embedding = LocalTFIDFEmbeddingRetriever(self.corpus)
  ```
- **Build Time:** Extremely fast. On 30 tables, building both BM25 and TF-IDF indexes takes **~3.2 milliseconds**. On 46 tables (`novacart_ecommerce.db`), it takes **~5.1 milliseconds**.

### 4.2 Cross-Database Isolation Analysis
- **Singleton Pattern:** The module instantiates a global singleton:
  [`hybrid_retriever = HybridSchemaRetriever()`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/hybrid.py#L126).
- **Isolation Defect:** If the application changes the database path in `Settings` while running, `hybrid_retriever` continues holding the corpus and vector matrix of the old database until manually re-instantiated.
- **Missing Scoping:** There is no concept of `retriever_for(database_id)`. Indexes are not keyed by database ID or tenant ID.

---

## 5. Domain Coupling and Fallback Vulnerabilities

| Component | Hardcoded Coupling | Behavior on Arbitrary Non-Ecommerce Schema | Severity |
| :--- | :--- | :--- | :--- |
| **`DOMAIN_DESCRIPTIONS`** | 30 e-commerce table descriptions in [`corpus.py:11`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/corpus.py#L11). | New tables receive generic string: `"General Operational Data"`. Cosine similarity loses semantic discrimination. | Medium |
| **`SYNONYM_TABLE_MAP`** | 50 keyword mappings in [`retriever.py:11`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L11). | Matches keywords like `"revenue"` to `["orders", "payments"]`. Fails if tables are named `invoices` or `billing`. | High |
| **`SchemaGrounder` Default**| [`retriever.py:78`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/retriever.py#L78): If no tables match query, defaults to: `selected.add("orders")`. | If new database has no table named `orders`, attempts to ground query on non-existent table. | Critical |
| **`ValueLinker` Mappings** | [`value_linker.py:19`](file:///c:/D_drive/AI_FOR_BI_P/backend/app/retrieval/value_linker.py#L19): Maps VIP, delivered, card, black friday. | Zero effect on non-ecommerce schemas; never links domain-specific entity values dynamically. | Medium |

---

## 6. Evaluation and Verification Evidence

- In unit test [`backend/tests/test_hybrid_retrieval.py`](file:///c:/D_drive/AI_FOR_BI_P/backend/tests/test_hybrid_retrieval.py), hybrid retrieval was verified across 10 benchmark queries:
  - Query `"monthly revenue trend"` correctly ranked `orders` as #1 table.
  - Query `"customer lifetime value and segments"` correctly retrieved `customers`, `customer_segments`, and `customer_segment_history`.
  - Query `"inventory levels across warehouses"` expanded join from `inventory` to `warehouses`.
- In gold benchmark test (`scripts/run_evaluation.py`), schema retrieval precision achieved **100% on the 25 benchmark queries** designed for `ecommerce.sqlite`.
- **Missing Coverage:** Retrieval has **never been evaluated on non-ecommerce databases** (e.g. Pagila/DVD Rental, Northwind, MIMIC-III healthcare, or GitHub schema).

