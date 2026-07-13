"""API version 1 routes."""

from fastapi import APIRouter

from rag_enterprise.api.v1.endpoints import health

api_v1_router = APIRouter()
api_v1_router.include_router(health.router, tags=["health"])
