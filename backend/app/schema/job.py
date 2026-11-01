"""
Asynchronous preparation job manager.
Runs schema profiling in the background, updates progress states, and enables non-blocking onboarding.
"""

import asyncio
from datetime import datetime, timezone
from typing import Dict, Optional
import uuid
from backend.app.core.logging import logger
from backend.app.schema.models import JobStatusEnum, PreparationJobState
from backend.app.schema.service import schema_service


class SchemaJobManager:
    """Manages asynchronous schema preparation jobs."""

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
        """
        async with self._lock:
            fingerprint = schema_service.compute_source_fingerprint()

            # Check existing succeeded job
            if not force_refresh and self._latest_job_id:
                latest = self._jobs.get(self._latest_job_id)
                if latest and latest.status == JobStatusEnum.SUCCEEDED and latest.source_fingerprint == fingerprint:
                    logger.info("Reusing existing succeeded preparation job.")
                    return latest

            # Check if job is currently running
            if self._latest_job_id:
                latest = self._jobs.get(self._latest_job_id)
                if latest and latest.status in [JobStatusEnum.PENDING, JobStatusEnum.RUNNING]:
                    logger.info(f"Preparation job {latest.job_id} already running.")
                    return latest

            job_id = str(uuid.uuid4())
            state = PreparationJobState(
                job_id=job_id,
                status=JobStatusEnum.PENDING,
                progress_percent=0,
                message="Preparation job queued",
                source_fingerprint=fingerprint,
            )
            self._jobs[job_id] = state
            self._latest_job_id = job_id

            # Launch asynchronous task
            asyncio.create_task(self._run_job_worker(job_id, force_refresh))
            return state

    async def _run_job_worker(self, job_id: str, force_refresh: bool):
        """Worker task executing the profiling process."""
        state = self._jobs[job_id]
        state.status = JobStatusEnum.RUNNING
        state.message = "Introspecting database tables..."
        state.started_at = datetime.now(timezone.utc)

        loop = asyncio.get_running_loop()

        def sync_progress_callback(processed: int, total: int, current_table: str):
            state.tables_processed = processed
            state.total_tables = total
            state.current_table = current_table
            percent = int((processed / total) * 100) if total > 0 else 0
            state.progress_percent = percent
            state.message = f"Profiling table {processed}/{total}: {current_table}"

        try:
            # Run CPU/disk bound profiling in default thread pool executor to not block event loop
            catalog = await loop.run_in_executor(
                None,
                lambda: schema_service.profile_database(
                    force_refresh=force_refresh,
                    progress_callback=sync_progress_callback,
                ),
            )

            state.status = JobStatusEnum.SUCCEEDED
            state.progress_percent = 100
            state.tables_processed = catalog.total_tables
            state.total_tables = catalog.total_tables
            state.current_table = None
            state.completed_at = datetime.now(timezone.utc)
            state.message = f"Successfully profiled {catalog.total_tables} tables and {catalog.total_rows:,} rows."
            logger.info(f"Schema preparation job {job_id} completed successfully.")

        except Exception as e:
            logger.error(f"Preparation job {job_id} failed: {e}", exc_info=True)
            state.status = JobStatusEnum.FAILED
            state.error = str(e)
            state.completed_at = datetime.now(timezone.utc)
            state.message = f"Preparation failed: {str(e)}"


job_manager = SchemaJobManager()

