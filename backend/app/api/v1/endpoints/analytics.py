"""
backend/app/api/v1/endpoints/analytics.py
API endpoints for Domain-Independent AI Data Analyst & Data Scientist Engine (Phase 4).
Supports intent classification, analytical planning, unified execution, and conversational follow-ups.
"""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from backend.app.analysis.contracts_v2 import (
    AnalyticalPlan,
    IntentCategory,
    IntentClassificationResult,
    StandardizedAnalyticalResult,
)
from backend.app.analysis.intent_classifier import intent_classifier
from backend.app.analysis.orchestrator import analytical_orchestrator
from backend.app.analysis.planner import analytical_planner
from backend.app.core.models import APIResponse
from backend.app.schema.service import schema_service

router = APIRouter(prefix="/analytics", tags=["Domain-Independent Analytical Intelligence"])


class AnalyticsQueryRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)
    session_id: Optional[str] = Field(default=None, description="Conversational context session ID")
    intent_override: Optional[IntentCategory] = Field(default=None)


class AnalyticsClassifyRequest(BaseModel):
    question: str = Field(..., min_length=2, max_length=1000)


@router.post(
    "/classify",
    response_model=APIResponse[IntentClassificationResult],
    summary="Classify question into IntentCategory and ComplexityLevel using ML",
)
async def classify_intent(
    body: AnalyticsClassifyRequest, request: Request
) -> APIResponse[IntentClassificationResult]:
    request_id = getattr(request.state, "request_id", None)
    result = intent_classifier.classify(body.question)
    return APIResponse(success=True, data=result, request_id=request_id)


@router.post(
    "/plan",
    response_model=APIResponse[AnalyticalPlan],
    summary="Generate schema-grounded AnalyticalPlan for user question",
)
async def generate_plan(
    body: AnalyticsQueryRequest, request: Request
) -> APIResponse[AnalyticalPlan]:
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog()
    plan = analytical_planner.create_plan(
        question=body.question,
        catalog=catalog,
        intent_override=body.intent_override,
    )
    return APIResponse(success=True, data=plan, request_id=request_id)


@router.post(
    "/execute",
    response_model=APIResponse[StandardizedAnalyticalResult],
    summary="Execute end-to-end analytical intelligence workflow",
)
async def execute_analysis(
    body: AnalyticsQueryRequest, request: Request
) -> APIResponse[StandardizedAnalyticalResult]:
    request_id = getattr(request.state, "request_id", None)
    catalog = schema_service.get_cached_catalog()
    if not catalog:
        raise HTTPException(status_code=400, detail="No active database connected or profiled.")

    result = analytical_orchestrator.analyze(
        question=body.question,
        session_id=body.session_id,
        catalog=catalog,
    )
    return APIResponse(success=result.success, data=result, request_id=request_id)


@router.get(
    "/evaluate-classifier",
    response_model=APIResponse[Dict[str, Any]],
    summary="Evaluate intent classifier Accuracy, Precision, Recall, and F1 on held-out split",
)
async def evaluate_classifier(request: Request) -> APIResponse[Dict[str, Any]]:
    request_id = getattr(request.state, "request_id", None)
    eval_metrics = intent_classifier.evaluate()
    return APIResponse(success=True, data=eval_metrics, request_id=request_id)

