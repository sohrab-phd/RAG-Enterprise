"""Health check endpoint for liveness and readiness probes."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel, Field

from rag_enterprise import __version__
from rag_enterprise.core.dependencies.providers import SettingsDep

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str = Field(description="Overall health status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="UTC timestamp of the health check")
    environment: str = Field(description="Deployment environment")


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """Return application health status.

    TODO: Add dependency checks (PostgreSQL, Redis) when integrations are wired.
    """
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(UTC),
        "environment": settings.app_env,
    }
