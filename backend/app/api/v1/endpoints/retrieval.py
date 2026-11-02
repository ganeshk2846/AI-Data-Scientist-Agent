"""
backend/app/api/v1/endpoints/retrieval.py
API endpoints for hybrid schema retrieval diagnostics and dynamic semantic layer metrics.
Supports LanceDB + BM25 RRF search, dynamic metric inference, and 3-tier provenance approvals.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from backend.app.core.contracts import MetricStatus, SemanticMetricDefinition
from backend.app.core.models import APIResponse
from backend.app.retrieval.hybrid import HybridRetrievalResult, hybrid_retriever
from backend.app.retrieval.semantics import (
    BusinessMetric,
    dynamic_semantic_engine,
    semantic_registry,
)
from backend.app.retrieval.value_linker import LinkedValue, value_linker
from backend.app.schema.service import schema_service

router = APIRouter(prefix="/retrieval", tags=["Hybrid Schema Retrieval & Semantics"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=15)


class MetricApproveRequest(BaseModel):
    metric_key: str = Field(..., min_length=1)
    approved_by: str = Field(default="user")


class RetrievalDiagnosticPayload(BaseModel):
    query: str
    hybrid_result: HybridRetrievalResult
    linked_values: List[LinkedValue]
    relevant_metrics: List[BusinessMetric]


@router.post(
    "/search",
    response_model=APIResponse[RetrievalDiagnosticPayload],
    summary="Run persistent hybrid BM25 + LanceDB RRF retrieval with value linking",
)
async def search_retrieval(
    body: RetrievalSearchRequest,
    request: Request,
) -> APIResponse[RetrievalDiagnosticPayload]:
    request_id = getattr(request.state, "request_id", None)
    retrieval_res = hybrid_retriever.retrieve(body.query, top_k=body.top_k)
    linked = value_linker.link_values(body.query)
    metrics = semantic_registry.find_relevant_metrics(body.query)

    payload = RetrievalDiagnosticPayload(
        query=body.query,
        hybrid_result=retrieval_res,
        linked_values=linked,
        relevant_metrics=metrics,
    )
    return APIResponse(success=True, data=payload, request_id=request_id)


@router.get(
    "/metrics",
    response_model=APIResponse[List[BusinessMetric]],
    summary="List verified semantic business definitions (v1 compatibility)",
)
async def list_metrics(request: Request) -> APIResponse[List[BusinessMetric]]:
    request_id = getattr(request.state, "request_id", None)
    metrics = semantic_registry.list_metrics()
    return APIResponse(success=True, data=metrics, request_id=request_id)


@router.get(
    "/metrics/authoritative",
    response_model=APIResponse[List[SemanticMetricDefinition]],
    summary="List authoritative USER_APPROVED business metrics for active database",
)
async def list_authoritative_metrics(request: Request) -> APIResponse[List[SemanticMetricDefinition]]:
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog()
    fp = getattr(catalog, "fingerprint", None) if catalog else None
    metrics = dynamic_semantic_engine.get_authoritative_metrics(fingerprint=fp)
    return APIResponse(success=True, data=metrics, request_id=request_id)


@router.post(
    "/metrics/infer",
    response_model=APIResponse[List[SemanticMetricDefinition]],
    summary="Trigger dynamic metric inference on active database schema using local LLM",
)
async def infer_metrics(request: Request) -> APIResponse[List[SemanticMetricDefinition]]:
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog() or schema_service.profile_database(force_refresh=False)
    if not catalog:
        raise HTTPException(status_code=400, detail="Active database catalog not available.")
    inferred = dynamic_semantic_engine.infer_metrics_from_schema(catalog)
    return APIResponse(success=True, data=inferred, request_id=request_id)


@router.post(
    "/metrics/approve",
    response_model=APIResponse[SemanticMetricDefinition],
    summary="Approve candidate metric to USER_APPROVED authoritative status",
)
async def approve_metric(
    body: MetricApproveRequest,
    request: Request,
) -> APIResponse[SemanticMetricDefinition]:
    request_id = getattr(request.state, "request_id", None)
    approved = dynamic_semantic_engine.approve_metric(body.metric_key, approved_by=body.approved_by)
    if not approved:
        raise HTTPException(status_code=404, detail=f"Metric '{body.metric_key}' not found.")
    return APIResponse(success=True, data=approved, request_id=request_id)
