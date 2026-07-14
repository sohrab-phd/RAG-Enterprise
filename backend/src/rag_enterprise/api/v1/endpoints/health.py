"""Operational health endpoints (RC1.2): /live, /ready, /system (+ legacy /health)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Response, status
from pydantic import BaseModel, ConfigDict, Field

from rag_enterprise import __version__
from rag_enterprise.core.dependencies.providers import SettingsDep
from rag_enterprise.core.health import build_system_inventory, evaluate_readiness

router = APIRouter()


class HealthResponse(BaseModel):
    """Legacy health check response schema."""

    model_config = ConfigDict(frozen=True)

    status: str = Field(description="Overall health status")
    version: str = Field(description="Application version")
    timestamp: datetime = Field(description="UTC timestamp of the health check")
    environment: str = Field(description="Deployment environment")


class LiveResponse(BaseModel):
    """Liveness probe — process is running; no dependency checks."""

    model_config = ConfigDict(frozen=True)

    status: Literal["live"] = "live"
    timestamp: datetime


class ReadyCheckDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    ok: bool
    detail: str


class ReadyResponse(BaseModel):
    """Readiness probe — dependencies required to serve traffic."""

    model_config = ConfigDict(frozen=True)

    status: Literal["ready", "not_ready"]
    timestamp: datetime
    checks: list[ReadyCheckDTO]


class SystemProviderDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    mode: str


class SystemModelsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    llm_model_key: str
    embedding_model_key: str
    embedding_dimensions: int
    prompt_template_version: str


class SystemCountsDTO(BaseModel):
    model_config = ConfigDict(frozen=True)

    documents: int
    chunks: int
    embeddings: int
    evaluation_runs: int
    ok: bool
    detail: str


class SystemResponse(BaseModel):
    """Operator inventory endpoint — config + counts; no provider calls."""

    model_config = ConfigDict(frozen=True)

    version: str
    environment: str
    providers: dict[str, SystemProviderDTO]
    models: SystemModelsDTO
    counts: SystemCountsDTO
    configuration_validated: bool
    dependency_injection_initialized: bool
    timestamp: datetime


@router.get(
    "/live",
    response_model=LiveResponse,
    status_code=status.HTTP_200_OK,
    summary="Liveness probe",
    tags=["health"],
)
async def live() -> LiveResponse:
    """Return immediately without dependency checks."""
    return LiveResponse(timestamp=datetime.now(UTC))


@router.get(
    "/ready",
    response_model=ReadyResponse,
    responses={
        200: {"description": "All readiness checks passed"},
        503: {"description": "One or more readiness checks failed"},
    },
    summary="Readiness probe",
    tags=["health"],
)
async def ready(settings: SettingsDep, response: Response) -> ReadyResponse:
    """Verify DI, configuration, database, evaluation storage, and upload storage."""
    report = await evaluate_readiness(settings)
    if not report.ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadyResponse(
        status="ready" if report.ready else "not_ready",
        timestamp=datetime.now(UTC),
        checks=[
            ReadyCheckDTO(name=item.name, ok=item.ok, detail=item.detail) for item in report.checks
        ],
    )


@router.get(
    "/system",
    response_model=SystemResponse,
    responses={
        200: {"description": "System inventory"},
        503: {"description": "Application container not ready for inventory"},
    },
    summary="System inventory",
    tags=["health"],
)
async def system(settings: SettingsDep, response: Response) -> SystemResponse:
    """Return version, environment, configured providers/models, and entity counts."""
    inventory = await build_system_inventory(settings)
    if not inventory["dependency_injection_initialized"]:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    providers_raw = inventory["providers"]
    models_raw = inventory["models"]
    counts_raw = inventory["counts"]
    return SystemResponse(
        version=str(inventory["version"]),
        environment=str(inventory["environment"]),
        providers={
            key: SystemProviderDTO(name=str(value["name"]), mode=str(value["mode"]))
            for key, value in providers_raw.items()
        },
        models=SystemModelsDTO(
            llm_model_key=str(models_raw["llm_model_key"]),
            embedding_model_key=str(models_raw["embedding_model_key"]),
            embedding_dimensions=int(models_raw["embedding_dimensions"]),
            prompt_template_version=str(models_raw["prompt_template_version"]),
        ),
        counts=SystemCountsDTO(
            documents=int(counts_raw["documents"]),
            chunks=int(counts_raw["chunks"]),
            embeddings=int(counts_raw["embeddings"]),
            evaluation_runs=int(counts_raw["evaluation_runs"]),
            ok=bool(counts_raw["ok"]),
            detail=str(counts_raw["detail"]),
        ),
        configuration_validated=bool(inventory["configuration_validated"]),
        dependency_injection_initialized=bool(inventory["dependency_injection_initialized"]),
        timestamp=datetime.now(UTC),
    )


@router.get("/health", response_model=HealthResponse, tags=["health"])
async def health_check(settings: SettingsDep) -> dict[str, Any]:
    """Legacy health check (kept for compatibility). Prefer /live and /ready."""
    return {
        "status": "healthy",
        "version": __version__,
        "timestamp": datetime.now(UTC),
        "environment": settings.app_env,
    }
