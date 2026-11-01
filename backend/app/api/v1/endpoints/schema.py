"""
API endpoints for schema catalog, table introspection, and asynchronous preparation jobs.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request, status
from backend.app.core.errors import ResourceNotFoundError
from backend.app.core.models import APIResponse
from backend.app.schema.job import job_manager
from backend.app.schema.models import DatabaseCatalog, PreparationJobState, TableModel
from backend.app.schema.service import schema_service

router = APIRouter(prefix="/schema", tags=["Schema & Catalog"])


@router.post(
    "/prepare",
    response_model=APIResponse[PreparationJobState],
    summary="Trigger asynchronous schema preparation job",
)
async def prepare_schema(
    request: Request,
    force: bool = Query(default=False, description="Force re-profiling even if cache is fresh"),
) -> APIResponse[PreparationJobState]:
    """
    Initiates an asynchronous schema introspection and profiling job.
    Idempotent: Reuses existing cache if database fingerprint is unchanged and force=False.
    """
    request_id = getattr(request.state, "request_id", None)
    job_state = await job_manager.start_preparation_job(force_refresh=force)
    return APIResponse(success=True, data=job_state, request_id=request_id)


@router.get(
    "/status",
    response_model=APIResponse[Dict[str, Any]],
    summary="Check schema preparation status",
)
async def get_schema_status(request: Request) -> APIResponse[Dict[str, Any]]:
    """Returns the current preparation job status and cached catalog summary."""
    request_id = getattr(request.state, "request_id", None)
    latest_job = job_manager.get_latest_job()

    cached_catalog = schema_service.get_cached_catalog()
    is_prepared = cached_catalog is not None

    summary = {
        "is_prepared": is_prepared,
        "latest_job": latest_job.model_dump() if latest_job else None,
        "catalog_summary": {
            "total_tables": cached_catalog.total_tables if cached_catalog else 0,
            "total_rows": cached_catalog.total_rows if cached_catalog else 0,
            "generated_at": cached_catalog.generated_at if cached_catalog else None,
            "source_fingerprint": cached_catalog.source_fingerprint if cached_catalog else None,
        } if cached_catalog else None,
    }
    return APIResponse(success=True, data=summary, request_id=request_id)


@router.get(
    "/jobs/{job_id}",
    response_model=APIResponse[PreparationJobState],
    summary="Get status of specific preparation job",
)
async def get_job_status(job_id: str, request: Request) -> APIResponse[PreparationJobState]:
    """Retrieves progress state and metrics for a specific background job ID."""
    request_id = getattr(request.state, "request_id", None)
    job = job_manager.get_job(job_id)
    if not job:
        raise ResourceNotFoundError(f"Preparation job not found: {job_id}")
    return APIResponse(success=True, data=job, request_id=request_id)


@router.get(
    "/catalog",
    response_model=APIResponse[DatabaseCatalog],
    summary="Retrieve full schema catalog",
)
async def get_catalog(request: Request) -> APIResponse[DatabaseCatalog]:
    """Returns the complete typed database catalog across all tables."""
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog()
    if not catalog:
        # If not cached yet, profile synchronously
        catalog = schema_service.profile_database(force_refresh=False)
    return APIResponse(success=True, data=catalog, request_id=request_id)


@router.get(
    "/tables",
    response_model=APIResponse[List[Dict[str, Any]]],
    summary="List all cataloged tables with summary statistics",
)
async def list_tables(request: Request) -> APIResponse[List[Dict[str, Any]]]:
    """Lists all tables with row count, column count, PKs, and FK count."""
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)

    tables_summary = []
    for name, tbl in sorted(catalog.tables.items()):
        tables_summary.append({
            "name": name,
            "row_count": tbl.row_count,
            "column_count": len(tbl.columns),
            "primary_keys": tbl.primary_key_columns,
            "foreign_key_count": len(tbl.foreign_keys),
            "index_count": len(tbl.indexes),
        })

    return APIResponse(success=True, data=tables_summary, request_id=request_id)


@router.get(
    "/tables/{table_name}",
    response_model=APIResponse[TableModel],
    summary="Get detailed schema profile for a single table",
)
async def get_table(table_name: str, request: Request) -> APIResponse[TableModel]:
    """Returns complete schema, column metrics, null rates, and indexes for a specific table."""
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)

    tbl = catalog.tables.get(table_name)
    if not tbl:
        # Case insensitive lookup fallback
        for k, v in catalog.tables.items():
            if k.lower() == table_name.lower():
                tbl = v
                break

    if not tbl:
        raise ResourceNotFoundError(
            f"Table '{table_name}' was not found in the catalog.",
            details={"available_tables": list(catalog.tables.keys())},
        )

    return APIResponse(success=True, data=tbl, request_id=request_id)

