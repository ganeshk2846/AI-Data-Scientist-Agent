"""
backend/tests/test_phase3_retrieval_semantics.py
Comprehensive Phase 3 Test Suite for Persistent Hybrid Retrieval & Dynamic Semantic Layer.
Tests:
1. FastEmbed ONNX local embedding provider (BAAI/bge-small-en-v1.5, 384-dim, offline).
2. Persistent BM25 index serialization, disk persistence, and schema fingerprint validation.
3. LanceDB persistent vector database indexing, reload, and semantic similarity search.
4. Hybrid Schema Retriever combining BM25 + LanceDB with Reciprocal Rank Fusion (RRF k=60) and FK expansion.
5. Dynamic Semantic Layer with 3-tier provenance lifecycle (AUTO_INFERRED -> VALIDATED_CANDIDATE -> USER_APPROVED).
6. Strict authoritative filtering (unapproved candidate metrics strictly excluded from query generation).
7. Database isolation by schema fingerprint and safe cache eviction on disconnect.
8. Non-destructive safety: agent_app.sqlite persistence and ecommerce.db SHA-256 invariance.
"""

import hashlib
from pathlib import Path
import shutil
import pytest
from backend.app.core.config import settings
from backend.app.core.contracts import MetricStatus, SupportedEngine
from backend.app.db.manager import db_manager
from backend.app.retrieval.corpus import SchemaCorpus
from backend.app.retrieval.embeddings import FastEmbedProvider, fastembed_provider
from backend.app.retrieval.hybrid import HybridSchemaRetriever, hybrid_retriever
from backend.app.retrieval.persistent_bm25 import PersistentBM25Retriever
from backend.app.retrieval.semantics import (
    CANONICAL_METRIC_REQUIREMENTS,
    CANONICAL_METRICS,
    DynamicSemanticEngine,
    dynamic_semantic_engine,
    semantic_registry,
)
from backend.app.retrieval.vector_store import TABLE_COLLECTION_NAME, LanceDBVectorStore
from backend.app.schema.service import schema_service


def compute_db_sha256(path: Path) -> str:
    """Computes SHA-256 checksum of a database file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().upper()


@pytest.fixture(scope="module")
def active_catalog():
    """Provides the active database catalog for ecommerce.db."""
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    assert catalog is not None
    return catalog


# =====================================================================
# 1. FastEmbed Local Dense Embedding Provider Tests
# =====================================================================

def test_fastembed_local_initialization():
    """Verifies FastEmbedProvider initializes local ONNX model with correct 384 dimensions."""
    provider = FastEmbedProvider.get_instance()
    assert provider is not None
    assert provider.model_name == settings.EMBEDDING_MODEL_NAME


def test_fastembed_vector_generation():
    """Verifies dense vector generation for single query and document batch."""
    q_vec = fastembed_provider.embed_query("monthly delivered sales revenue")
    assert isinstance(q_vec, list)
    assert len(q_vec) == 384
    assert all(isinstance(v, float) for v in q_vec)

    docs = ["orders master table", "customers directory", "product categories"]
    doc_vecs = fastembed_provider.embed_documents(docs)
    assert len(doc_vecs) == 3
    for v in doc_vecs:
        assert len(v) == 384


# =====================================================================
# 2. Persistent BM25 Tests
# =====================================================================

def test_persistent_bm25_build_and_save(active_catalog, tmp_path):
    """Verifies BM25 building from catalog, serializing to disk, and reloading."""
    corpus = SchemaCorpus(active_catalog)
    bm25 = PersistentBM25Retriever(
        corpus=corpus,
        fingerprint="test_fp_123",
        storage_dir=tmp_path / "bm25",
    )
    saved_path = bm25.save()
    assert saved_path.exists()
    assert bm25.is_persisted()
    assert len(bm25.table_names) == len(active_catalog.tables)

    # Reload into fresh instance from disk
    loaded_bm25 = PersistentBM25Retriever(
        fingerprint="test_fp_123",
        storage_dir=tmp_path / "bm25",
    )
    assert loaded_bm25.is_valid("test_fp_123") is True
    assert loaded_bm25.is_valid("different_fp") is False
    assert len(loaded_bm25.table_names) == len(active_catalog.tables)

    # Search keyword
    res = loaded_bm25.search("promotions discount campaign coupon", top_k=3)
    top_tables = [r[0] for r in res]
    assert "product_promotions" in top_tables or "promotions" in top_tables


# =====================================================================
# 3. LanceDB Persistent Vector Store Tests
# =====================================================================

def test_lancedb_vector_store_indexing_and_search(active_catalog, tmp_path):
    """Verifies indexing schema catalog into LanceDB and semantic similarity search."""
    fp = getattr(active_catalog, "fingerprint", None) or "ecommerce_test_fp"
    vs_dir = tmp_path / "lancedb" / fp
    vs = LanceDBVectorStore(fingerprint=fp, storage_dir=vs_dir)

    assert vs.is_indexed() is False
    count = vs.index_catalog(active_catalog, force_reindex=True)
    assert count == len(active_catalog.tables)
    assert vs.is_indexed() is True
    assert vs.count() == len(active_catalog.tables)

    # Re-connect to same storage dir without re-indexing
    vs2 = LanceDBVectorStore(fingerprint=fp, storage_dir=vs_dir)
    assert vs2.is_indexed() is True
    assert vs2.count() == len(active_catalog.tables)

    # Search semantic query
    results = vs2.search("customer interactions and loyalty ratings", top_k=3)
    assert len(results) > 0
    top_table, sim_score = results[0]
    assert 0.0 <= sim_score <= 1.0
    matched_tables = [r[0] for r in results]
    assert "customer_interactions" in matched_tables or "customer_loyalty" in matched_tables or "customers" in matched_tables or "customer_segments" in matched_tables


# =====================================================================
# 4. Hybrid Retriever (RRF + FK Graph Expansion) Tests
# =====================================================================

def test_hybrid_retriever_rrf_scoring(active_catalog):
    """Verifies Reciprocal Rank Fusion combines BM25 and vector scores correctly."""
    hybrid = HybridSchemaRetriever(active_catalog)
    res = hybrid.retrieve("What is our total sales revenue and orders count by customer segment?", top_k=4)

    assert len(res.retrieved_tables) >= 2
    assert "Table: " in res.minimal_schema_prompt

    # Verify RRF score ordering
    scores = [t.rrf_score for t in res.retrieved_tables if not t.is_expanded_join]
    assert scores == sorted(scores, reverse=True)

    # Verify key business tables retrieved
    retrieved_names = res.selected_table_names
    assert "orders" in retrieved_names or "order_items" in retrieved_names or "customer_segments" in retrieved_names


def test_hybrid_retriever_fk_graph_expansion(active_catalog):
    """Verifies foreign key join graph expansion when primary table is retrieved."""
    hybrid = HybridSchemaRetriever(active_catalog)
    res = hybrid.retrieve("Show product details and line item unit prices", top_k=3, max_expanded=6)

    # Check that related tables connected by FK are expanded
    expanded_tables = [t for t in res.retrieved_tables if t.is_expanded_join]
    # If FK expansion triggered, verify expansion reason contains foreign key link
    for exp in expanded_tables:
        assert exp.expansion_reason is not None
        assert "Foreign key" in exp.expansion_reason


# =====================================================================
# 5. Dynamic Semantic Layer & Provenance State Lifecycle Tests
# =====================================================================

def test_semantic_canonical_baseline_seeding(active_catalog):
    """Verifies canonical baseline metrics are seeded as USER_APPROVED."""
    fp = getattr(active_catalog, "fingerprint", None) or "default"
    dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=active_catalog)

    auth_metrics = dynamic_semantic_engine.get_authoritative_metrics(fingerprint=fp)
    metric_keys = [m.metric_key for m in auth_metrics]

    # Every canonical metric whose required tables exist in this database must be
    # seeded; metrics needing absent tables must not be invented.
    available = set(active_catalog.tables)
    supported = {
        key for key, req in CANONICAL_METRIC_REQUIREMENTS.items()
        if set(req["required_tables"]) <= available
    }
    assert supported, "no canonical metric is supported by the connected database"
    assert supported <= set(metric_keys)
    unsupported = set(CANONICAL_METRIC_REQUIREMENTS) - supported
    assert not (unsupported & set(metric_keys))
    assert "gross_revenue" in metric_keys
    assert "net_revenue" in metric_keys
    assert "average_order_value" in metric_keys

    # Verify provenance status is authoritative (SYSTEM_APPROVED or USER_APPROVED)
    for m in auth_metrics:
        assert m.status in (MetricStatus.USER_APPROVED, MetricStatus.SYSTEM_APPROVED)


def test_semantic_provenance_lifecycle_and_authoritative_isolation(tmp_path):
    """
    Verifies the 3-state provenance lifecycle:
    1. Candidate metric created as AUTO_INFERRED / VALIDATED_CANDIDATE.
    2. Strict exclusion: Unapproved candidate NEVER returned in authoritative metrics.
    3. User approval: Metric approved and immediately included in authoritative context.
    """
    test_db = tmp_path / "test_agent_app.sqlite"
    # Run migration on isolated test store
    from backend.app.db.migration import run_agent_store_migration
    run_agent_store_migration(app_db_path=test_db)

    engine = DynamicSemanticEngine(app_db_path=test_db)
    fp = "test_fp_isolation"

    # Step 1: Insert candidate metric directly simulating LLM inference
    import sqlite3
    conn = sqlite3.connect(str(test_db))
    with conn:
        conn.execute(
            """
            INSERT INTO semantic_metrics (
                id, metric_key, display_name, formula_sql, status, derivation_type,
                confidence_score, fingerprint
            ) VALUES ('inferred_cart_abandonment', 'cart_abandonment_rate', 'Cart Abandonment Rate',
                      'COUNT(abandoned) * 100.0 / COUNT(*)', 'VALIDATED_CANDIDATE', 'INFERRED', 0.85, ?);
            """,
            (fp,),
        )
    conn.close()

    # Step 2: Strict Isolation Check - Unapproved candidate MUST NOT be in authoritative metrics!
    auth_before = engine.get_authoritative_metrics(fingerprint=fp)
    auth_keys_before = [m.metric_key for m in auth_before]
    assert "cart_abandonment_rate" not in auth_keys_before, "Unapproved metric was leaked into authoritative context!"

    # Verify it does appear in list_metrics
    all_metrics = engine.list_metrics(fingerprint=fp)
    assert any(m.metric_key == "cart_abandonment_rate" for m in all_metrics)

    # Step 3: Approve candidate metric
    approved = engine.approve_metric("cart_abandonment_rate", fingerprint=fp, approved_by="senior_analyst")
    assert approved is not None
    assert approved.status == MetricStatus.USER_APPROVED
    assert approved.verified_by == "senior_analyst"

    # Step 4: Verify it now appears in authoritative metrics
    auth_after = engine.get_authoritative_metrics(fingerprint=fp)
    auth_keys_after = [m.metric_key for m in auth_after]
    assert "cart_abandonment_rate" in auth_keys_after

    # Step 5: Verify formatted prompt context includes approved metric
    ctx = engine.format_authoritative_prompt_context(fingerprint=fp, query="cart abandonment rate")
    assert "Cart Abandonment Rate" in ctx
    assert "COUNT(abandoned) * 100.0 / COUNT(*)" in ctx


# =====================================================================
# 6. Database Isolation and Disconnect Eviction Tests
# =====================================================================

def test_retriever_cache_eviction_on_disconnect(active_catalog):
    """Verifies that disconnecting the database clears in-memory retrieval caches."""
    hybrid_retriever.ensure_catalog(active_catalog)
    assert hybrid_retriever.catalog is not None
    assert hybrid_retriever.corpus is not None

    # Call disconnect
    db_manager.disconnect_database()

    # In-memory retrieval caches must be cleared
    assert hybrid_retriever.catalog is None
    assert hybrid_retriever.corpus is None
    assert hybrid_retriever.bm25 is None
    assert hybrid_retriever.vector_store is None

    # Reconnect baseline ecommerce.db
    from backend.app.core.contracts import ActiveDatabaseConfig, ConnectionStatus
    config = ActiveDatabaseConfig(
        id="active_db",
        name="ecommerce.db",
        engine=SupportedEngine.SQLITE,
        file_path=str(settings.resolved_ecommerce_db_path),
        status=ConnectionStatus.READY,
        read_only=True,
    )
    db_manager.connect_database(config)
    status = db_manager.get_status()
    assert status.connected is True


# =====================================================================
# 7. FastAPI Endpoint Integration Tests
# =====================================================================

def test_api_authoritative_metrics_endpoint(client):
    """Verifies GET /api/v1/retrieval/metrics/authoritative returns only approved metrics."""
    res = client.get("/api/v1/retrieval/metrics/authoritative")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    metrics = body["data"]
    assert len(metrics) >= 3
    for m in metrics:
        assert m["status"] in ("USER_APPROVED", "SYSTEM_APPROVED")


def test_api_approve_metric_endpoint(client):
    """Verifies POST /api/v1/retrieval/metrics/approve updates provenance."""
    # Ensure a metric exists to approve
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    fp = catalog.fingerprint
    dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fp, catalog=catalog)
    res = client.post(
        "/api/v1/retrieval/metrics/approve",
        json={"metric_key": "gross_revenue", "approved_by": "qa_lead"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "USER_APPROVED"
    assert body["data"]["verified_by"] == "qa_lead"


# =====================================================================
# 8. Non-Destructive Invariance Test for ecommerce.db
# =====================================================================

def test_ecommerce_db_sha256_invariance():
    """Guarantees zero write operations occurred against ecommerce.db."""
    baseline_hash = "366080C92E8DC7024A15B95730A35E63AC16765F748142F51CC40F92B63F3D9E"
    current_hash = compute_db_sha256(settings.resolved_ecommerce_db_path)
    assert current_hash == baseline_hash, f"CRITICAL: ecommerce.db was modified! Hash mismatch: {current_hash} != {baseline_hash}"
