"""
backend/app/retrieval/embeddings.py
FastEmbed ONNX local dense embedding retriever & backward-compatible TF-IDF retriever.
Runs 100% locally with zero cloud API dependencies.
"""

from abc import ABC, abstractmethod
import threading
from typing import List, Optional, Tuple
from fastembed import TextEmbedding
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.corpus import SchemaCorpus


class BaseEmbeddingRetriever(ABC):
    @abstractmethod
    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        pass


class FastEmbedProvider:
    """
    Local ONNX embedding generator powered by fastembed.
    Loads BAAI/bge-small-en-v1.5 (or configured model) into memory lazily and safely.
    Zero external cloud network calls at runtime.
    """

    _instance: Optional["FastEmbedProvider"] = None
    _lock = threading.Lock()

    def __init__(self, model_name: Optional[str] = None):
        self.model_name = model_name or settings.EMBEDDING_MODEL_NAME
        self._embedder: Optional[TextEmbedding] = None
        self._init_lock = threading.Lock()

    def _get_embedder(self) -> TextEmbedding:
        if self._embedder is None:
            with self._init_lock:
                if self._embedder is None:
                    logger.info(f"Initializing FastEmbed ONNX model: {self.model_name}")
                    self._embedder = TextEmbedding(model_name=self.model_name)
                    logger.info("FastEmbed ONNX model initialized successfully.")
        return self._embedder

    @classmethod
    def get_instance(cls, model_name: Optional[str] = None) -> "FastEmbedProvider":
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(model_name=model_name)
        return cls._instance

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Generates dense vector embeddings for a list of text strings."""
        if not texts:
            return []
        embedder = self._get_embedder()
        embeddings_iter = embedder.embed(texts)
        return [emb.tolist() if hasattr(emb, "tolist") else list(emb) for emb in embeddings_iter]

    def embed_query(self, query: str) -> List[float]:
        """Generates a dense vector embedding for a query string."""
        embedder = self._get_embedder()
        res = list(embedder.embed([query]))
        emb = res[0]
        return emb.tolist() if hasattr(emb, "tolist") else list(emb)


fastembed_provider = FastEmbedProvider.get_instance()


class LocalTFIDFEmbeddingRetriever(BaseEmbeddingRetriever):
    """
    Local semantic retriever based on TF-IDF vector space cosine similarity.
    Retained for backward compatibility with Version 1 test suites.
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
