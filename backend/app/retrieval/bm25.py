"""
BM25 Lexical Schema Retriever using rank-bm25.
Scores table relevance based on exact term matches, column names, and domain keywords.
"""

from typing import Dict, List, Tuple
from rank_bm25 import BM25Okapi
from backend.app.retrieval.corpus import SchemaCorpus, tokenize_text


class BM25Retriever:
    """Lexical table retriever using BM25Okapi."""

    def __init__(self, corpus: SchemaCorpus):
        self.corpus = corpus
        self.table_names = list(corpus.documents.keys())
        self.tokenized_corpus = [corpus.documents[t].tokens for t in self.table_names]
        self.bm25 = BM25Okapi(self.tokenized_corpus)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Ranks tables by BM25 relevance score.
        Returns list of (table_name, bm25_score) tuples sorted in descending order.
        """
        query_tokens = tokenize_text(query)
        if not query_tokens:
            return [(t, 0.0) for t in self.table_names[:top_k]]

        scores = self.bm25.get_scores(query_tokens)
        scored_pairs = list(zip(self.table_names, scores))
        # Sort descending by score
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return scored_pairs[:top_k]

