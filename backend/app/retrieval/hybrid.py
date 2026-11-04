"""
backend/app/retrieval/hybrid.py
Upgraded Persistent Hybrid Schema Retriever with Reciprocal Rank Fusion (RRF).
Combines persistent BM25 lexical precision with LanceDB dense vector similarity (FastEmbed ONNX),
followed by Foreign-Key Graph Expansion for optimal join path discovery.
"""

import threading
from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from backend.app.core.logging import logger
from backend.app.retrieval.corpus import SchemaCorpus, tokenize_text
from backend.app.retrieval.embeddings import LocalTFIDFEmbeddingRetriever, fastembed_provider
from backend.app.retrieval.persistent_bm25 import PersistentBM25Retriever
from backend.app.retrieval.vector_store import LanceDBVectorStore
from backend.app.schema.models import DatabaseCatalog
from backend.app.schema.service import schema_service

RRF_K = 60  # Standard constant in information retrieval


class RetrievedTable(BaseModel):
    table_name: str
    domain: str
    rrf_score: float
    bm25_score: float
    bm25_rank: int
    embedding_score: float
    embedding_rank: int
    is_expanded_join: bool = False
    expansion_reason: Optional[str] = None


class HybridRetrievalResult(BaseModel):
    query: str
    retrieved_tables: List[RetrievedTable]
    selected_table_names: List[str]
    minimal_schema_prompt: str


class HybridSchemaRetriever:
    """Combines persistent BM25 lexical ranking and LanceDB vector retrieval with Reciprocal Rank Fusion."""

    def __init__(self, catalog: Optional[DatabaseCatalog] = None):
        self._lock = threading.RLock()
        # The module-level singleton is constructed at import time, before any
        # database has been connected through the self-service setup flow, so a
        # missing or unreachable database must not prevent the app from starting.
        resolved_catalog = catalog
        if resolved_catalog is None:
            try:
                resolved_catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
            except Exception as exc:
                logger.warning(f"No catalogue available at retriever construction: {exc}")
                resolved_catalog = None
        self.catalog = resolved_catalog
        self.corpus: Optional[SchemaCorpus] = None
        self.bm25: Optional[PersistentBM25Retriever] = None
        self.vector_store: Optional[LanceDBVectorStore] = None
        self.fallback_embedding: Optional[LocalTFIDFEmbeddingRetriever] = None

        if self.catalog:
            self._initialize_retrievers(self.catalog)

    def _initialize_retrievers(self, catalog: DatabaseCatalog) -> None:
        """Initializes both persistent BM25 and LanceDB vector stores for catalog."""
        fp = getattr(catalog, "fingerprint", None) or getattr(catalog, "source_fingerprint", None) or "default"
        self.catalog = catalog
        self.corpus = SchemaCorpus(self.catalog)
        self.fallback_embedding = LocalTFIDFEmbeddingRetriever(self.corpus)

        # 1. Initialize persistent BM25
        self.bm25 = PersistentBM25Retriever(corpus=self.corpus, fingerprint=fp)
        if not self.bm25.is_persisted():
            try:
                self.bm25.save()
            except Exception as e:
                logger.warning(f"Could not persist BM25 index: {e}")

        # 2. Initialize persistent LanceDB vector store
        self.vector_store = LanceDBVectorStore(fingerprint=fp)
        if not self.vector_store.is_indexed():
            try:
                self.vector_store.index_catalog(catalog)
            except Exception as e:
                logger.warning(f"Could not index catalog in LanceDB: {e}")

    def ensure_catalog(self, catalog: Optional[DatabaseCatalog] = None) -> None:
        """Ensures retriever indexes the latest active database catalog."""
        with self._lock:
            target = catalog or schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
            if target is not None:
                current_fp = getattr(self.catalog, "fingerprint", None) if self.catalog else None
                target_fp = getattr(target, "fingerprint", None)
                if self.catalog is None or current_fp != target_fp or not self.corpus or not self.corpus.documents:
                    self._initialize_retrievers(target)

    def retrieve(
        self,
        query: str,
        top_k: int = 5,
        max_expanded: int = 7,
        catalog: Optional[DatabaseCatalog] = None,
    ) -> HybridRetrievalResult:
        with self._lock:
            self.ensure_catalog(catalog)
            if not self.corpus or not self.catalog:
                raise RuntimeError("HybridSchemaRetriever catalog is not available.")

            # 1. BM25 Lexical Search
            bm25_results: List[Tuple[str, float]] = []
            if self.bm25:
                bm25_results = self.bm25.search(query, top_k=20)
            bm25_ranks = {tbl: rank for rank, (tbl, _) in enumerate(bm25_results, start=1)}
            bm25_scores = {tbl: float(score) for tbl, score in bm25_results}

            # 2. Dense Vector Search via LanceDB (with fallback to TF-IDF if unindexed)
            embed_results: List[Tuple[str, float]] = []
            if self.vector_store and self.vector_store.is_indexed():
                try:
                    embed_results = self.vector_store.search(query, top_k=20)
                except Exception as e:
                    logger.warning(f"LanceDB search failed, falling back to local TF-IDF: {e}")
                    if self.fallback_embedding:
                        embed_results = self.fallback_embedding.search(query, top_k=20)
            elif self.fallback_embedding:
                embed_results = self.fallback_embedding.search(query, top_k=20)

            embed_ranks = {tbl: rank for rank, (tbl, _) in enumerate(embed_results, start=1)}
            embed_scores = {tbl: float(score) for tbl, score in embed_results}

            # 3. Reciprocal Rank Fusion (RRF)
            all_candidates = set(bm25_ranks.keys()).union(set(embed_ranks.keys()))
            rrf_scores: Dict[str, float] = {}

            for tbl in all_candidates:
                b_rank = bm25_ranks.get(tbl, 100)
                e_rank = embed_ranks.get(tbl, 100)
                score = (1.0 / (RRF_K + b_rank)) + (1.0 / (RRF_K + e_rank))
                rrf_scores[tbl] = score

            # Sort descending by RRF score
            sorted_rrf = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)
            top_initial = sorted_rrf[:top_k]

            selected_table_map: Dict[str, RetrievedTable] = {}
            for tbl, rrf_val in top_initial:
                doc = self.corpus.documents.get(tbl)
                domain_desc = doc.domain if doc else "Operational data"
                selected_table_map[tbl] = RetrievedTable(
                    table_name=tbl,
                    domain=domain_desc,
                    rrf_score=round(rrf_val, 4),
                    bm25_score=round(bm25_scores.get(tbl, 0.0), 4),
                    bm25_rank=bm25_ranks.get(tbl, 999),
                    embedding_score=round(embed_scores.get(tbl, 0.0), 4),
                    embedding_rank=embed_ranks.get(tbl, 999),
                    is_expanded_join=False,
                )

            # 4. Foreign Key Graph Expansion
            current_tables = list(selected_table_map.keys())
            q_tokens = set(tokenize_text(query))

            for tbl_name in current_tables:
                tbl_model = self.catalog.tables.get(tbl_name)
                if not tbl_model:
                    continue

                for fk in tbl_model.foreign_keys:
                    target = fk.target_table
                    if target in self.catalog.tables and target not in selected_table_map and len(selected_table_map) < max_expanded:
                        target_tokens = set(tokenize_text(target))
                        is_match = bool(q_tokens.intersection(target_tokens)) or any(
                            t.startswith(q) or q.startswith(t) for q in q_tokens for t in target_tokens
                        )
                        if (is_match or len(selected_table_map) < 4) and target in self.corpus.documents:
                            doc = self.corpus.documents[target]
                            selected_table_map[target] = RetrievedTable(
                                table_name=target,
                                domain=doc.domain,
                                rrf_score=0.01,
                                bm25_score=0.0,
                                bm25_rank=999,
                                embedding_score=0.0,
                                embedding_rank=999,
                                is_expanded_join=True,
                                expansion_reason=f"Foreign key join link: {tbl_name}.{fk.source_column} -> {target}.{fk.target_column}",
                            )

            final_tables = list(selected_table_map.values())
            final_names = [t.table_name for t in final_tables]
            minimal_prompt = self.catalog.to_minimal_prompt_schema(final_names)

            return HybridRetrievalResult(
                query=query,
                retrieved_tables=final_tables,
                selected_table_names=final_names,
                minimal_schema_prompt=minimal_prompt,
            )


hybrid_retriever = HybridSchemaRetriever()
