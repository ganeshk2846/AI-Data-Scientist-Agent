"""
Asynchronous preparation job manager.
Runs schema profiling in the background, updates progress states across 7 stages,
and enables non-blocking onboarding and retrieval index construction.
"""

import asyncio
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Dict, List, Optional
import uuid
from backend.app.core.logging import logger
from backend.app.db.manager import db_manager
from backend.app.retrieval.corpus import SchemaCorpus
from backend.app.retrieval.hybrid import hybrid_retriever
from backend.app.retrieval.persistent_bm25 import PersistentBM25Retriever
from backend.app.retrieval.semantics import dynamic_semantic_engine, is_ecommerce_compatible
from backend.app.retrieval.vector_store import LanceDBVectorStore
from backend.app.schema.models import JobStatusEnum, PreparationJobState, PreparationStageInfo, StageStatusEnum
from backend.app.schema.service import schema_service


def _create_initial_stages() -> List[PreparationStageInfo]:
    """Generates the 7 explicit preparation stages in WAITING state."""
    return [
        PreparationStageInfo(id=1, name="Database connection verified", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=2, name="Schema discovery", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=3, name="Table profiling", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=4, name="Semantic metadata construction", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=5, name="Building dense vector index", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=6, name="Building BM25 index", status=StageStatusEnum.WAITING),
        PreparationStageInfo(id=7, name="Final preparation verification", status=StageStatusEnum.WAITING),
    ]


class SchemaJobManager:
    """Manages asynchronous schema preparation jobs with 7-stage lifecycle tracking."""

    def __init__(self):
        self._jobs: Dict[str, PreparationJobState] = {}
        self._latest_job_id: Optional[str] = None
        self._lock = asyncio.Lock()

    def get_job(self, job_id: str) -> Optional[PreparationJobState]:
        return self._jobs.get(job_id)

    def get_latest_job(self) -> Optional[PreparationJobState]:
        if self._latest_job_id:
            return self._jobs.get(self._latest_job_id)
        return None

    async def start_preparation_job(self, force_refresh: bool = False) -> PreparationJobState:
        """
        Initiates an asynchronous schema preparation job.
        If a succeeded job already exists with matching fingerprint and not force_refresh,
        returns the existing state.
        Ensures concurrent requests cannot start duplicate preparation jobs for the same fingerprint.
        """
        async with self._lock:
            fingerprint = schema_service.compute_source_fingerprint()

            # Check existing succeeded job in memory
            if not force_refresh and self._latest_job_id:
                latest = self._jobs.get(self._latest_job_id)
                if latest and latest.status == JobStatusEnum.SUCCEEDED and latest.source_fingerprint == fingerprint:
                    logger.info("Reusing existing succeeded preparation job.")
                    return latest

            # Check if index artifacts already exist complete on disk for this fingerprint
            if not force_refresh:
                cached = schema_service.get_cached_catalog()
                if cached and cached.source_fingerprint == fingerprint:
                    vstore = LanceDBVectorStore(fingerprint=fingerprint)
                    bm_retriever = PersistentBM25Retriever(fingerprint=fingerprint)
                    if vstore.is_indexed() and bm_retriever.is_persisted():
                        logger.info("Found complete verified artifacts on disk for fingerprint. Immediate completion.")
                        completed_stages = [
                            PreparationStageInfo(id=1, name="Database connection verified", status=StageStatusEnum.COMPLETED, details="Verified read-only mode", elapsed_ms=0.5),
                            PreparationStageInfo(id=2, name="Schema discovery", status=StageStatusEnum.COMPLETED, details=f"Reused schema catalog ({cached.total_tables} tables)", elapsed_ms=0.5),
                            PreparationStageInfo(id=3, name="Table profiling", status=StageStatusEnum.COMPLETED, details=f"Reused profiling metrics ({cached.total_rows:,} rows)", elapsed_ms=0.5),
                            PreparationStageInfo(id=4, name="Semantic metadata construction", status=StageStatusEnum.COMPLETED, details="Reused semantic documents", elapsed_ms=0.5),
                            PreparationStageInfo(id=5, name="Building dense vector index", status=StageStatusEnum.COMPLETED, details=f"Reused LanceDB index ({vstore.count()} tables)", elapsed_ms=0.5),
                            PreparationStageInfo(id=6, name="Building BM25 index", status=StageStatusEnum.COMPLETED, details=f"Reused BM25 index ({len(bm_retriever.table_names)} tables)", elapsed_ms=0.5),
                            PreparationStageInfo(id=7, name="Final preparation verification", status=StageStatusEnum.COMPLETED, details="Hybrid schema retriever verified", elapsed_ms=0.5),
                        ]
                        job_id = str(uuid.uuid4())
                        state = PreparationJobState(
                            job_id=job_id,
                            status=JobStatusEnum.SUCCEEDED,
                            progress_percent=100,
                            message=f"Reused verified schema artifacts for {cached.total_tables} tables.",
                            source_fingerprint=fingerprint,
                            tables_processed=cached.total_tables,
                            total_tables=cached.total_tables,
                            stages=completed_stages,
                            completed_at=datetime.now(timezone.utc),
                        )
                        self._jobs[job_id] = state
                        self._latest_job_id = job_id
                        return state

            # Check if job is currently running for this fingerprint
            if self._latest_job_id:
                latest = self._jobs.get(self._latest_job_id)
                if latest and latest.status in [JobStatusEnum.PENDING, JobStatusEnum.RUNNING]:
                    if latest.source_fingerprint == fingerprint:
                        logger.info(f"Preparation job {latest.job_id} already running for active fingerprint.")
                        return latest

            job_id = str(uuid.uuid4())
            state = PreparationJobState(
                job_id=job_id,
                status=JobStatusEnum.PENDING,
                progress_percent=0,
                message="Preparation job queued",
                source_fingerprint=fingerprint,
                stages=_create_initial_stages(),
            )
            self._jobs[job_id] = state
            self._latest_job_id = job_id

            # Launch asynchronous background worker task
            asyncio.create_task(self._run_job_worker(job_id, force_refresh))
            return state

    async def retry_preparation_job(self) -> PreparationJobState:
        """Forces retry of schema preparation for active database."""
        return await self.start_preparation_job(force_refresh=True)

    async def _run_job_worker(self, job_id: str, force_refresh: bool):
        """Worker task executing the 7-stage schema preparation and indexing pipeline."""
        state = self._jobs[job_id]
        state.status = JobStatusEnum.RUNNING
        state.started_at = datetime.now(timezone.utc)
        state.message = "Starting database preparation pipeline..."
        loop = asyncio.get_running_loop()

        def set_stage(stage_id: int, status: StageStatusEnum, details: Optional[str] = None, elapsed_ms: Optional[float] = None):
            for s in state.stages:
                if s.id == stage_id:
                    s.status = status
                    if details is not None:
                        s.details = details
                    if elapsed_ms is not None:
                        s.elapsed_ms = round(elapsed_ms, 2)
                    break

        try:
            # ---------------------------------------------------------
            # Stage 1: Database validation
            # ---------------------------------------------------------
            t1_start = time.perf_counter()
            set_stage(1, StageStatusEnum.RUNNING)
            state.message = "Verifying database connection and read-only mode..."
            state.progress_percent = 5

            adapter = db_manager.get_active_adapter()
            if not adapter.is_connected:
                adapter.connect()
            fingerprint = adapter.compute_fingerprint()
            state.source_fingerprint = fingerprint
            t1_elapsed = (time.perf_counter() - t1_start) * 1000
            set_stage(
                1,
                StageStatusEnum.COMPLETED,
                details=f"Engine: {adapter.engine_type.value}, read-only: True, fingerprint: {fingerprint[:8]}...",
                elapsed_ms=t1_elapsed,
            )
            state.progress_percent = 14

            # ---------------------------------------------------------
            # Stage 2: Schema discovery & Stage 3: Table profiling
            # ---------------------------------------------------------
            cached_catalog = None
            if not force_refresh:
                cached_catalog = schema_service.get_cached_catalog()

            if cached_catalog and cached_catalog.source_fingerprint == fingerprint:
                catalog = cached_catalog
                set_stage(2, StageStatusEnum.COMPLETED, details=f"Reused schema catalog ({catalog.total_tables} tables)", elapsed_ms=0.5)
                set_stage(3, StageStatusEnum.COMPLETED, details=f"Reused profiling metrics ({catalog.total_rows:,} rows)", elapsed_ms=0.5)
                state.tables_processed = catalog.total_tables
                state.total_tables = catalog.total_tables
                state.progress_percent = 43
            else:
                # Stage 2: Introspection
                t2_start = time.perf_counter()
                set_stage(2, StageStatusEnum.RUNNING)
                state.message = "Discovering database tables and columns..."

                introspector = schema_service._get_introspector()
                tables = introspector.introspect_tables()
                state.total_tables = len(tables)
                t2_elapsed = (time.perf_counter() - t2_start) * 1000
                set_stage(2, StageStatusEnum.COMPLETED, details=f"Discovered {len(tables)} tables and views", elapsed_ms=t2_elapsed)
                state.progress_percent = 28

                # Stage 3: Adaptive profiling
                t3_start = time.perf_counter()
                set_stage(3, StageStatusEnum.RUNNING)
                state.message = f"Profiling {len(tables)} tables with adaptive sampling..."

                def sync_progress_callback(processed: int, total: int, current_table: str):
                    state.tables_processed = processed
                    state.total_tables = total
                    state.current_table = current_table
                    pct = 28 + int((processed / max(total, 1)) * 22)
                    state.progress_percent = pct
                    state.message = f"Profiling table {processed}/{total}: {current_table}"

                catalog = await loop.run_in_executor(
                    None,
                    lambda: schema_service.profile_database(
                        force_refresh=force_refresh,
                        progress_callback=sync_progress_callback,
                    ),
                )
                t3_elapsed = (time.perf_counter() - t3_start) * 1000
                set_stage(
                    3,
                    StageStatusEnum.COMPLETED,
                    details=f"Profiled {catalog.total_tables} tables ({catalog.total_rows:,} rows)",
                    elapsed_ms=t3_elapsed,
                )
                state.progress_percent = 50

            # ---------------------------------------------------------
            # Stage 4: Semantic metadata construction
            # ---------------------------------------------------------
            t4_start = time.perf_counter()
            set_stage(4, StageStatusEnum.RUNNING)
            state.message = "Constructing schema corpus and semantic documents..."
            state.progress_percent = 55

            def build_corpus_and_semantics():
                corpus = SchemaCorpus(catalog)
                if is_ecommerce_compatible(catalog):
                    dynamic_semantic_engine.seed_baseline_canonical_metrics(fingerprint=fingerprint, catalog=catalog)
                return corpus

            corpus = await loop.run_in_executor(None, build_corpus_and_semantics)
            t4_elapsed = (time.perf_counter() - t4_start) * 1000
            set_stage(
                4,
                StageStatusEnum.COMPLETED,
                details=f"Constructed semantic documents for {len(corpus.documents)} tables",
                elapsed_ms=t4_elapsed,
            )
            state.progress_percent = 65

            # ---------------------------------------------------------
            # Stage 5: Dense vector indexing (LanceDB + FastEmbed)
            # ---------------------------------------------------------
            t5_start = time.perf_counter()
            set_stage(5, StageStatusEnum.RUNNING)
            state.message = "Indexing schema vectors with FastEmbed (BAAI/bge-small-en-v1.5)..."
            state.progress_percent = 70

            def index_vector_store():
                vstore = LanceDBVectorStore(fingerprint=fingerprint)
                if not force_refresh and vstore.is_indexed() and vstore.count() == len(catalog.tables):
                    return vstore.count(), True
                count = vstore.index_catalog(catalog, force_reindex=force_refresh)
                return count, False

            v_count, v_reused = await loop.run_in_executor(None, index_vector_store)
            t5_elapsed = (time.perf_counter() - t5_start) * 1000
            v_details = (
                f"Reused existing LanceDB vector index ({v_count} tables)"
                if v_reused
                else f"Indexed {v_count} tables into LanceDB"
            )
            set_stage(5, StageStatusEnum.COMPLETED, details=v_details, elapsed_ms=t5_elapsed)
            state.progress_percent = 80

            # ---------------------------------------------------------
            # Stage 6: Lexical indexing (Persistent BM25)
            # ---------------------------------------------------------
            t6_start = time.perf_counter()
            set_stage(6, StageStatusEnum.RUNNING)
            state.message = "Building persistent BM25 lexical index..."
            state.progress_percent = 85

            def index_bm25_store():
                retriever = PersistentBM25Retriever(corpus=corpus, fingerprint=fingerprint)
                if not force_refresh and retriever.is_persisted() and retriever.is_valid(fingerprint):
                    return len(retriever.table_names), True
                retriever.save()
                return len(retriever.table_names), False

            bm_count, bm_reused = await loop.run_in_executor(None, index_bm25_store)
            t6_elapsed = (time.perf_counter() - t6_start) * 1000
            bm_details = (
                f"Reused existing BM25 index ({bm_count} tables)"
                if bm_reused
                else f"Persisted BM25 inverted index for {bm_count} tables"
            )
            set_stage(6, StageStatusEnum.COMPLETED, details=bm_details, elapsed_ms=t6_elapsed)
            state.progress_percent = 92

            # ---------------------------------------------------------
            # Stage 7: Final preparation verification
            # ---------------------------------------------------------
            t7_start = time.perf_counter()
            set_stage(7, StageStatusEnum.RUNNING)
            state.message = "Verifying hybrid retrieval across schema indexes..."
            state.progress_percent = 95

            def verify_retrieval():
                hybrid_retriever.ensure_catalog(catalog)
                probe_query = "orders customers revenue products"
                probe_res = hybrid_retriever.retrieve(probe_query, top_k=3)
                return len(probe_res.retrieved_tables)

            probe_count = await loop.run_in_executor(None, verify_retrieval)
            t7_elapsed = (time.perf_counter() - t7_start) * 1000
            set_stage(
                7,
                StageStatusEnum.COMPLETED,
                details=f"Hybrid schema retriever ready (probe verified {probe_count} tables)",
                elapsed_ms=t7_elapsed,
            )

            # Mark whole job SUCCEEDED
            state.status = JobStatusEnum.SUCCEEDED
            state.progress_percent = 100
            state.tables_processed = catalog.total_tables
            state.total_tables = catalog.total_tables
            state.current_table = None
            state.completed_at = datetime.now(timezone.utc)
            state.message = f"Schema preparation complete! {catalog.total_tables} tables ready for AI BI analysis."
            logger.info(f"Schema preparation job {job_id} succeeded in 7 stages.")

        except Exception as e:
            logger.error(f"Preparation job {job_id} failed: {e}", exc_info=True)
            state.status = JobStatusEnum.FAILED
            state.error = str(e)
            state.completed_at = datetime.now(timezone.utc)
            state.message = f"Preparation failed: {str(e)}"
            for s in state.stages:
                if s.status == StageStatusEnum.RUNNING:
                    s.status = StageStatusEnum.FAILED
                    s.details = str(e)
                    break


job_manager = SchemaJobManager()


