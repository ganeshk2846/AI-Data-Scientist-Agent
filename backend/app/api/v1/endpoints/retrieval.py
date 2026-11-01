"""
API endpoints for hybrid schema retrieval diagnostics and semantic metric definitions.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field
from backend.app.core.models import APIResponse
from backend.app.retrieval.hybrid import HybridRetrievalResult, hybrid_retriever
from backend.app.retrieval.semantics import BusinessMetric, semantic_registry
from backend.app.retrieval.value_linker import LinkedValue, value_linker

router = APIRouter(prefix="/retrieval", tags=["Hybrid Schema Retrieval & Semantics"])


class RetrievalSearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=500)
    top_k: int = Field(default=5, ge=1, le=15)


class RetrievalDiagnosticPayload(BaseModel):
    query: str
    hybrid_result: HybridRetrievalResult
    linked_values: List[LinkedValue]
    relevant_metrics: List[BusinessMetric]


@router.post(
    "/search",
    response_model=APIResponse[RetrievalDiagnosticPayload],
    summary="Run hybrid BM25 + Embedding RRF retrieval with value linking",
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
    summary="List verified semantic business definitions",
)
async def list_metrics(request: Request) -> APIResponse[List[BusinessMetric]]:
    request_id = getattr(request.state, "request_id", None)
    metrics = semantic_registry.list_metrics()
    return APIResponse(success=True, data=metrics, request_id=request_id)
