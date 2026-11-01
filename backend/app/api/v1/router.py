"""
API v1 Router aggregator.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import analysis, chat, health, retrieval, schema

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(schema.router)
api_router.include_router(chat.router)
api_router.include_router(retrieval.router)
api_router.include_router(analysis.router)
