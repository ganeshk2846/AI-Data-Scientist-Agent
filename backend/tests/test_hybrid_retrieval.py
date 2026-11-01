"""
Tests for Phase 5: Hybrid Schema Retrieval, BM25, TF-IDF Embeddings, RRF, Value Linking, and Semantics.
"""

from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.corpus import SchemaCorpus
from backend.app.retrieval.embeddings import LocalTFIDFEmbeddingRetriever
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.retrieval.semantics import semantic_registry
from backend.app.retrieval.value_linker import value_linker
from backend.app.schema.service import schema_service


def test_schema_corpus_generation():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    corpus = SchemaCorpus(catalog)
    assert len(corpus.documents) == 30
    assert "orders" in corpus.documents
    assert len(corpus.documents["orders"].tokens) > 10


def test_bm25_retrieval():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    corpus = SchemaCorpus(catalog)
    bm25 = BM25Retriever(corpus)

    results = bm25.search("inventory warehouse snapshot", top_k=5)
    top_tables = [r[0] for r in results]
    assert "inventory" in top_tables or "warehouses" in top_tables


def test_embedding_retrieval():
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database()
    corpus = SchemaCorpus(catalog)
    embed = LocalTFIDFEmbeddingRetriever(corpus)

    results = embed.search("customer satisfaction support complaints", top_k=5)
    top_tables = [r[0] for r in results]
    assert "support_tickets" in top_tables or "reviews" in top_tables


def test_reciprocal_rank_fusion_and_fk_expansion():
    res = hybrid_retriever.retrieve("What is our top selling product category by revenue?", top_k=3)
    assert len(res.retrieved_tables) >= 2
    names = res.selected_table_names
    assert "products" in names or "categories" in names or "orders" in names
    assert "Table: " in res.minimal_schema_prompt


def test_value_linker():
    linked_vip = value_linker.link_values("How many VIP customers placed orders?")
    assert len(linked_vip) >= 1
    found_vip = any(l.exact_db_value == "VIP" and l.target_table == "customer_segments" for l in linked_vip)
    assert found_vip is True

    linked_status = value_linker.link_values("Show delivered orders paid with credit card")
    assert any(l.exact_db_value == "delivered" for l in linked_status)
    assert any(l.exact_db_value == "credit_card" for l in linked_status)


def test_semantic_metrics_registry():
    metrics = semantic_registry.list_metrics()
    assert len(metrics) >= 5

    rev = semantic_registry.get_metric("net_revenue")
    assert rev is not None
    assert "delivered" in rev.formula

    relevant = semantic_registry.find_relevant_metrics("What is our average order value and return rate?")
    rel_names = [m.name for m in relevant]
    assert "average_order_value" in rel_names or "return_rate" in rel_names


def test_api_retrieval_search_endpoint(client):
    res = client.post("/api/v1/retrieval/search", json={"query": "Show revenue for VIP customers", "top_k": 5})
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    data = body["data"]
    assert "hybrid_result" in data
    assert len(data["hybrid_result"]["retrieved_tables"]) > 0
    assert "linked_values" in data
    assert any(lv["exact_db_value"] == "VIP" for lv in data["linked_values"])


def test_api_retrieval_metrics_endpoint(client):
    res = client.get("/api/v1/retrieval/metrics")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    metrics = body["data"]
    assert len(metrics) >= 5
    assert any(m["name"] == "gross_revenue" for m in metrics)
