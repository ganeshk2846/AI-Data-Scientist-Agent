"""
Hybrid Schema Retriever with Reciprocal Rank Fusion (RRF) and Foreign-Key Graph Expansion.
Combines BM25 lexical precision with semantic embedding similarity, then expands join paths.
"""

from typing import Dict, List, Optional, Set, Tuple
from pydantic import BaseModel, Field
from backend.app.retrieval.bm25 import BM25Retriever
from backend.app.retrieval.corpus import SchemaCorpus, tokenize_text
from backend.app.retrieval.embeddings import LocalTFIDFEmbeddingRetriever
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
    """Combines BM25 lexical ranking and embedding retrieval with Reciprocal Rank Fusion."""

    def __init__(self, catalog: Optional[DatabaseCatalog] = None):
        self.catalog = catalog or schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
        self.corpus = SchemaCorpus(self.catalog)
        self.bm25 = BM25Retriever(self.corpus)
        self.embedding = LocalTFIDFEmbeddingRetriever(self.corpus)

    def retrieve(self, query: str, top_k: int = 5, max_expanded: int = 7) -> HybridRetrievalResult:
        # 1. BM25 Search
        bm25_results = self.bm25.search(query, top_k=20)
        bm25_ranks = {tbl: rank for rank, (tbl, _) in enumerate(bm25_results, start=1)}
        bm25_scores = {tbl: score for tbl, score in bm25_results}

        # 2. Embedding Search
        embed_results = self.embedding.search(query, top_k=20)
        embed_ranks = {tbl: rank for rank, (tbl, _) in enumerate(embed_results, start=1)}
        embed_scores = {tbl: score for tbl, score in embed_results}

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
            doc = self.corpus.documents[tbl]
            selected_table_map[tbl] = RetrievedTable(
                table_name=tbl,
                domain=doc.domain,
                rrf_score=round(rrf_val, 4),
                bm25_score=round(bm25_scores.get(tbl, 0.0), 4),
                bm25_rank=bm25_ranks.get(tbl, 999),
                embedding_score=round(embed_scores.get(tbl, 0.0), 4),
                embedding_rank=embed_ranks.get(tbl, 999),
                is_expanded_join=False,
            )

        # 4. Foreign Key Graph Expansion
        # Ensure join target tables are included if relevant
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
                    # Check if query shares tokens with target table or column, or expand key domain links
                    is_match = bool(q_tokens.intersection(target_tokens)) or any(t.startswith(q) or q.startswith(t) for q in q_tokens for t in target_tokens)
                    if is_match or len(selected_table_map) < 4:
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
