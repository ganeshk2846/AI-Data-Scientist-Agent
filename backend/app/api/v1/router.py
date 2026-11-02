"""
API v1 Router aggregator.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import analysis, analytics, chat, health, memory, ops, retrieval, schema

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(schema.router)
api_router.include_router(chat.router)
api_router.include_router(retrieval.router)
api_router.include_router(analysis.router)
api_router.include_router(analytics.router)
api_router.include_router(memory.router)
api_router.include_router(ops.router)
