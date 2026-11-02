"""
backend/app/retrieval/vector_store.py
Persistent LanceDB Vector Store for Database Schema Metadata.
Uses FastEmbed ONNX dense embeddings (BAAI/bge-small-en-v1.5) for local vector similarity search.
Isolates collections per active database fingerprint with automatic on-disk persistence and reloading.
"""

from datetime import datetime, timezone
from pathlib import Path
import shutil
import threading
from typing import Any, Dict, List, Optional, Tuple
import lancedb
from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.retrieval.corpus import DOMAIN_DESCRIPTIONS, tokenize_text
from backend.app.retrieval.embeddings import FastEmbedProvider, fastembed_provider
from backend.app.schema.models import DatabaseCatalog


TABLE_COLLECTION_NAME = "schema_tables"


class LanceDBVectorStore:
    """
    Persistent vector database for schema search powered by LanceDB.
    Enforces isolation per database fingerprint with zero external API calls.
    """

    def __init__(
        self,
        fingerprint: Optional[str] = None,
        storage_dir: Optional[Path] = None,
        embedder: Optional[FastEmbedProvider] = None,
    ):
        self._lock = threading.RLock()
        self._custom_storage_dir = storage_dir is not None
        self.fingerprint = fingerprint or "default"
        self.storage_dir = storage_dir or (settings.resolved_lancedb_dir / self.fingerprint)
        self.embedder = embedder or fastembed_provider
        self._db: Optional[Any] = None

    def _get_db(self) -> Any:
        with self._lock:
            if self._db is None:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
                self._db = lancedb.connect(str(self.storage_dir))
            return self._db

    def is_indexed(self) -> bool:
        """Checks if schema table collection exists and contains indexed documents."""
        with self._lock:
            try:
                db = self._get_db()
                existing_tables = set(db.table_names() if hasattr(db, "table_names") else db.list_tables())
                if TABLE_COLLECTION_NAME not in existing_tables:
                    return False
                tbl = db.open_table(TABLE_COLLECTION_NAME)
                return tbl.count_rows() > 0
            except Exception as e:
                logger.debug(f"LanceDB is_indexed check returned False: {e}")
                return False

    def count(self) -> int:
        """Returns number of indexed schema documents."""
        with self._lock:
            try:
                db = self._get_db()
                existing_tables = set(db.table_names() if hasattr(db, "table_names") else db.list_tables())
                if TABLE_COLLECTION_NAME not in existing_tables:
                    return 0
                tbl = db.open_table(TABLE_COLLECTION_NAME)
                return tbl.count_rows()
            except Exception:
                return 0

    def index_catalog(
        self,
        catalog: DatabaseCatalog,
        embedder: Optional[FastEmbedProvider] = None,
        force_reindex: bool = False,
    ) -> int:
        """
        Embeds and indexes all tables and relationships from the database catalog into LanceDB.
        """
        with self._lock:
            active_embedder = embedder or self.embedder
            if not self._custom_storage_dir:
                fp = getattr(catalog, "fingerprint", None) or getattr(catalog, "source_fingerprint", None) or self.fingerprint
                self.fingerprint = fp
                self.storage_dir = settings.resolved_lancedb_dir / self.fingerprint

            # Check if index already valid on disk
            if not force_reindex and self.is_indexed():
                existing_count = self.count()
                if existing_count == len(catalog.tables):
                    logger.info(f"LanceDB index already up to date ({existing_count} tables, fp: {self.fingerprint})")
                    return existing_count

            logger.info(f"Indexing {len(catalog.tables)} tables into LanceDB (fingerprint: {self.fingerprint})")
            records: List[Dict[str, Any]] = []
            search_texts: List[str] = []

            for name, tbl in catalog.tables.items():
                domain_desc = DOMAIN_DESCRIPTIONS.get(name, tbl.description or "General Operational Data")
                col_names = [c.name for c in tbl.columns]

                col_details: List[str] = []
                safe_samples: List[str] = []
                for c in tbl.columns:
                    role_parts = []
                    if c.is_pk:
                        role_parts.append("primary key")
                    if c.is_fk:
                        role_parts.append(f"foreign key referencing {c.fk_target_table}.{c.fk_target_column}")
                    if c.is_date_candidate:
                        role_parts.append("date timestamp calendar")
                    if c.is_numeric_candidate:
                        role_parts.append("numeric metric amount money")
                    col_details.append(f"{c.name} ({c.sqlite_type}): {' '.join(role_parts)}")
                    if c.sample_values:
                        safe_samples.extend(c.sample_values[:5])

                fk_links = [
                    f"{fk.source_column} references {fk.target_table}.{fk.target_column}"
                    for fk in tbl.foreign_keys
                ]

                # Composite rich search text
                text_parts = [
                    f"Table name: {name}",
                    f"Description and business purpose: {domain_desc}",
                    f"Columns: {' '.join(col_names)}",
                    f"Column details: {' | '.join(col_details)}",
                    f"Foreign key links: {' | '.join(fk_links)}",
                    f"Sample values: {' '.join(safe_samples[:10])}",
                ]
                full_text = "\n".join(text_parts)
                search_texts.append(full_text)

                records.append({
                    "table_name": name,
                    "domain": domain_desc,
                    "columns_text": " ".join(col_names),
                    "relationships_text": " | ".join(fk_links),
                    "sample_values": " ".join(safe_samples[:10]),
                    "search_text": full_text,
                    "row_count": tbl.row_count,
                    "column_count": len(tbl.columns),
                    "fingerprint": self.fingerprint,
                })

            # Generate dense vector embeddings in batch
            vectors = active_embedder.embed_documents(search_texts)
            for record, vec in zip(records, vectors):
                record["vector"] = vec

            # Write to LanceDB
            db = self._get_db()
            db.create_table(TABLE_COLLECTION_NAME, records, mode="overwrite")
            indexed_count = len(records)
            logger.info(f"Successfully indexed {indexed_count} schema tables into LanceDB at {self.storage_dir}")
            return indexed_count

    def search(
        self,
        query: str,
        top_k: int = 10,
        embedder: Optional[FastEmbedProvider] = None,
    ) -> List[Tuple[str, float]]:
        """
        Searches LanceDB for tables semantically relevant to query.
        Returns list of (table_name, similarity_score) sorted descending by similarity.
        """
        with self._lock:
            if not self.is_indexed():
                return []

            active_embedder = embedder or self.embedder
            query_vector = active_embedder.embed_query(query)

            db = self._get_db()
            tbl = db.open_table(TABLE_COLLECTION_NAME)

            # Query with cosine distance
            results = tbl.search(query_vector).metric("cosine").limit(top_k).to_list()

            scored: List[Tuple[str, float]] = []
            for item in results:
                table_name = item.get("table_name", "")
                dist = float(item.get("_distance", 1.0))
                # Cosine distance in LanceDB is 1 - cosine_similarity
                sim = max(0.0, min(1.0, 1.0 - dist))
                scored.append((table_name, round(sim, 4)))

            scored.sort(key=lambda x: x[1], reverse=True)
            return scored[:top_k]

    def clear(self) -> None:
        """Drops schema table collection and cleans up directory."""
        with self._lock:
            try:
                db = self._get_db()
                existing_tables = set(db.table_names() if hasattr(db, "table_names") else db.list_tables())
                if TABLE_COLLECTION_NAME in existing_tables:
                    db.drop_table(TABLE_COLLECTION_NAME)
            except Exception as e:
                logger.warning(f"Error dropping LanceDB table: {e}")

            if self.storage_dir.exists():
                try:
                    shutil.rmtree(self.storage_dir, ignore_errors=True)
                except Exception as e:
                    logger.warning(f"Error removing LanceDB dir: {e}")
            self._db = None
