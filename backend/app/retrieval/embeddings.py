"""
Semantic Embedding Schema Retriever using local TF-IDF vector space model.
Computes cosine similarity against table domain descriptions and semantic roles.
"""

from abc import ABC, abstractmethod
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.retrieval.corpus import SchemaCorpus


class BaseEmbeddingRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        pass


class LocalTFIDFEmbeddingRetriever(BaseEmbeddingRetriever):
    """
    Local semantic retriever based on TF-IDF vector space cosine similarity.
    Provides fast, deterministic semantic ranking without requiring external vector DBs or cloud APIs.
    """

    def __init__(self, corpus: SchemaCorpus):
        self.corpus = corpus
        self.table_names = list(corpus.documents.keys())
        self.corpus_texts = [corpus.documents[t].search_text for t in self.table_names]

        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            sublinear_tf=True,
        )
        self.doc_matrix = self.vectorizer.fit_transform(self.corpus_texts)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.doc_matrix).flatten()

        scored_pairs = list(zip(self.table_names, similarities))
        scored_pairs.sort(key=lambda x: x[1], reverse=True)
        return [(t, float(score)) for t, score in scored_pairs[:top_k]]

