"""
backend/app/retrieval/persistent_bm25.py
Persistent BM25 Lexical Schema Retriever using rank-bm25.
Persists lexical inverted index, document statistics, and tokenized corpus to disk.
Supports fast startup, fingerprint validation, and on-demand cache rebuilding.
"""

from datetime import datetime, timezone
import os
from pathlib import Path
import pickle
import threading
from typing import Dict, List, Optional, Tuple
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.corpus import SchemaCorpus, tokenize_text
from backend.app.schema.models import DatabaseCatalog


class PersistentBM25Retriever:
    """
    Disk-persisted lexical table retriever using BM25Okapi.
    Isolates index per database fingerprint and reloads across restarts without re-tokenizing.
    """

    def __init__(
        self,
        corpus: Optional[SchemaCorpus] = None,
        fingerprint: Optional[str] = None,
        storage_dir: Optional[Path] = None,
    ):
        self._lock = threading.RLock()
        self._custom_storage_dir = storage_dir is not None
        self.fingerprint = fingerprint or (
            getattr(corpus.catalog, "fingerprint", None) or getattr(corpus.catalog, "source_fingerprint", None)
            if corpus and corpus.catalog else None
        )
        self.storage_dir = storage_dir or (settings.resolved_bm25_dir / (self.fingerprint or "default"))
        self.index_file = self.storage_dir / "bm25_index.pkl"

        self.corpus: Optional[SchemaCorpus] = corpus
        self.table_names: List[str] = []
        self.tokenized_corpus: List[List[str]] = []
        self.bm25: Optional[BM25Okapi] = None
        self.created_at: Optional[str] = None

        if corpus:
            self._build_from_corpus(corpus)
        elif self.fingerprint and self.is_persisted():
            self.load()

    def _build_from_corpus(self, corpus: SchemaCorpus) -> None:
        """Constructs in-memory BM25 index from SchemaCorpus."""
        with self._lock:
            self.corpus = corpus
            if not self.fingerprint:
                self.fingerprint = (
                    getattr(corpus.catalog, "fingerprint", None)
                    or getattr(corpus.catalog, "source_fingerprint", None)
                    or "default"
                )
            if not self._custom_storage_dir:
                self.storage_dir = settings.resolved_bm25_dir / (self.fingerprint or "default")
                self.index_file = self.storage_dir / "bm25_index.pkl"

            self.table_names = list(corpus.documents.keys())
            self.tokenized_corpus = [corpus.documents[t].tokens for t in self.table_names]
            self.bm25 = BM25Okapi(self.tokenized_corpus)
            self.created_at = datetime.now(timezone.utc).isoformat()
            logger.info(f"Built BM25 index for {len(self.table_names)} tables (fingerprint: {self.fingerprint})")

    def is_persisted(self) -> bool:
        """Returns True if persisted index file exists on disk."""
        return self.index_file.exists() and self.index_file.is_file()

    def is_valid(self, expected_fingerprint: str) -> bool:
        """Validates that loaded index matches expected database schema fingerprint."""
        return bool(self.bm25 and self.fingerprint and self.fingerprint == expected_fingerprint)

    def save(self, target_path: Optional[Path] = None) -> Path:
        """Persists the BM25 index and metadata to disk."""
        with self._lock:
            if not self.bm25:
                raise RuntimeError("Cannot save uninitialized BM25 index.")

            dest = target_path or self.index_file
            dest.parent.mkdir(parents=True, exist_ok=True)

            payload = {
                "fingerprint": self.fingerprint,
                "table_names": self.table_names,
                "tokenized_corpus": self.tokenized_corpus,
                "bm25": self.bm25,
                "created_at": self.created_at or datetime.now(timezone.utc).isoformat(),
            }

            temp_dest = dest.with_suffix(".tmp")
            with open(temp_dest, "wb") as f:
                pickle.dump(payload, f, protocol=pickle.HIGHEST_PROTOCOL)

            if dest.exists():
                os.replace(temp_dest, dest)
            else:
                temp_dest.rename(dest)

            logger.info(f"Persisted BM25 index to {dest} ({len(self.table_names)} tables)")
            return dest

    def load(self, source_path: Optional[Path] = None) -> bool:
        """Loads BM25 index from disk."""
        with self._lock:
            src = source_path or self.index_file
            if not src.exists():
                return False

            try:
                with open(src, "rb") as f:
                    payload = pickle.load(f)

                self.fingerprint = payload.get("fingerprint")
                self.table_names = payload.get("table_names", [])
                self.tokenized_corpus = payload.get("tokenized_corpus", [])
                self.bm25 = payload.get("bm25")
                self.created_at = payload.get("created_at")

                logger.info(f"Loaded persistent BM25 index from {src} ({len(self.table_names)} tables, fp: {self.fingerprint})")
                return True
            except Exception as e:
                logger.warning(f"Failed to load persistent BM25 index from {src}: {e}")
                return False

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float]]:
        """
        Ranks tables by BM25 relevance score.
        Returns list of (table_name, bm25_score) tuples sorted in descending order.
        """
        with self._lock:
            if not self.bm25:
                return [(t, 0.0) for t in self.table_names[:top_k]]

            query_tokens = tokenize_text(query)
            if not query_tokens:
                return [(t, 0.0) for t in self.table_names[:top_k]]

            scores = self.bm25.get_scores(query_tokens)
            scored_pairs = list(zip(self.table_names, scores))
            scored_pairs.sort(key=lambda x: x[1], reverse=True)
            return scored_pairs[:top_k]

    def clear(self) -> None:
        """Disposes in-memory state and removes persisted index file."""
        with self._lock:
            self.bm25 = None
            self.table_names = []
            self.tokenized_corpus = []
            if self.index_file.exists():
                try:
                    self.index_file.unlink()
                except Exception as e:
                    logger.warning(f"Failed to delete BM25 file {self.index_file}: {e}")
