"""
API v1 Router aggregator.
"""

from fastapi import APIRouter
from backend.app.api.v1.endpoints import chat, health, schema

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(health.router)
api_router.include_router(schema.router)
api_router.include_router(chat.router)
