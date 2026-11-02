"""
Schema retrieval and semantic intelligence package.
Phase 3 persistent hybrid retrieval with LanceDB, FastEmbed, and dynamic semantic layer.
"""

from backend.app.retrieval.corpus import SchemaCorpus, tokenize_text
from backend.app.retrieval.embeddings import (
    FastEmbedProvider,
    LocalTFIDFEmbeddingRetriever,
    fastembed_provider,
)
from backend.app.retrieval.hybrid import (
    HybridRetrievalResult,
    HybridSchemaRetriever,
    RetrievedTable,
    hybrid_retriever,
)
from backend.app.retrieval.persistent_bm25 import PersistentBM25Retriever
from backend.app.retrieval.semantics import (
    CANONICAL_METRICS,
    BusinessMetric,
    DynamicSemanticEngine,
    SemanticRegistry,
    dynamic_semantic_engine,
    semantic_registry,
)
from backend.app.retrieval.value_linker import LinkedValue, ValueLinker, value_linker
from backend.app.retrieval.vector_store import LanceDBVectorStore

__all__ = [
    "SchemaCorpus",
    "tokenize_text",
    "FastEmbedProvider",
    "fastembed_provider",
    "LocalTFIDFEmbeddingRetriever",
    "PersistentBM25Retriever",
    "LanceDBVectorStore",
    "HybridRetrievalResult",
    "RetrievedTable",
    "HybridSchemaRetriever",
    "hybrid_retriever",
    "BusinessMetric",
    "CANONICAL_METRICS",
    "DynamicSemanticEngine",
    "dynamic_semantic_engine",
    "SemanticRegistry",
    "semantic_registry",
    "LinkedValue",
    "ValueLinker",
    "value_linker",
]
