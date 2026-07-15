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
    backend: str | None = None
    provider: str | None = None
    model: str | None = None
    dimensions: int | None = None
    timeout_seconds: float | None = None
    reachability: str | None = None
    latency_ms: float | None = None
    loaded: bool | None = None
    index_compatible: bool | None = None
    reindex_required: bool | None = None


class SystemLlmDTO(BaseModel):
    """LLM execution configuration exposed on /system."""

    model_config = ConfigDict(frozen=True)

    backend: str
    provider: str
    model: str
    selected_model: str | None = None
    installed_models: list[str] = Field(default_factory=list)
    timeout_seconds: float
    ollama_version: str | None = None
    selection_mode: str | None = None
    reachability: str | None = None


class SystemEmbeddingDTO(BaseModel):
    """Embedding execution configuration exposed on /system."""

    model_config = ConfigDict(frozen=True)

    backend: str
    provider: str
    model: str
    dimensions: int
    loaded: bool | None = None
    index_compatible: bool | None = None
    reindex_required: bool | None = None
    indexed_model_keys: list[str] = Field(default_factory=list)
    indexed_dimensions: list[int] = Field(default_factory=list)
    detail: str | None = None


class SystemModelsCatalogDTO(BaseModel):
    """Developer inventory for GET /system/models."""

    model_config = ConfigDict(frozen=True)

    backend: str
    provider: str
    selection_mode: str | None = None
    selected_model: str | None = None
    installed_models: list[str] = Field(default_factory=list)
    base_url: str | None = None
    reachable: bool | None = None
    ollama_version: str | None = None
    detail: str | None = None


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
    """Operator inventory endpoint — config + counts; no provider writes."""

    model_config = ConfigDict(frozen=True)

    version: str
    environment: str
    providers: dict[str, SystemProviderDTO]
    llm: SystemLlmDTO
    embedding: SystemEmbeddingDTO
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
    llm_raw = inventory["llm"]
    embedding_raw = inventory["embedding"]
    return SystemResponse(
        version=str(inventory["version"]),
        environment=str(inventory["environment"]),
        providers={
            key: SystemProviderDTO(
                name=str(value["name"]),
                mode=str(value["mode"]),
                backend=(str(value["backend"]) if value.get("backend") is not None else None),
                provider=(str(value["provider"]) if value.get("provider") is not None else None),
                model=(str(value["model"]) if value.get("model") is not None else None),
                dimensions=(
                    int(value["dimensions"]) if value.get("dimensions") is not None else None
                ),
                timeout_seconds=(
                    float(value["timeout_seconds"])
                    if value.get("timeout_seconds") is not None
                    else None
                ),
                reachability=(
                    str(value["reachability"]) if value.get("reachability") is not None else None
                ),
                latency_ms=(
                    float(value["latency_ms"]) if value.get("latency_ms") is not None else None
                ),
                loaded=(bool(value["loaded"]) if value.get("loaded") is not None else None),
                index_compatible=(
                    bool(value["index_compatible"])
                    if value.get("index_compatible") is not None
                    else None
                ),
                reindex_required=(
                    bool(value["reindex_required"])
                    if value.get("reindex_required") is not None
                    else None
                ),
            )
            for key, value in providers_raw.items()
        },
        llm=SystemLlmDTO(
            backend=str(llm_raw["backend"]),
            provider=str(llm_raw["provider"]),
            model=str(llm_raw.get("selected_model") or llm_raw["model"]),
            selected_model=(
                str(llm_raw["selected_model"]) if llm_raw.get("selected_model") is not None else None
            ),
            installed_models=[str(item) for item in (llm_raw.get("installed_models") or [])],
            timeout_seconds=float(llm_raw["timeout_seconds"]),
            ollama_version=(
                str(llm_raw["ollama_version"]) if llm_raw.get("ollama_version") is not None else None
            ),
            selection_mode=(
                str(llm_raw["selection_mode"]) if llm_raw.get("selection_mode") is not None else None
            ),
            reachability=(
                str(llm_raw["reachability"]) if llm_raw.get("reachability") is not None else None
            ),
        ),
        embedding=SystemEmbeddingDTO(
            backend=str(embedding_raw["backend"]),
            provider=str(embedding_raw["provider"]),
            model=str(embedding_raw["model"]),
            dimensions=int(embedding_raw["dimensions"]),
            loaded=(
                bool(embedding_raw["loaded"]) if embedding_raw.get("loaded") is not None else None
            ),
            index_compatible=(
                bool(embedding_raw["index_compatible"])
                if embedding_raw.get("index_compatible") is not None
                else None
            ),
            reindex_required=(
                bool(embedding_raw["reindex_required"])
                if embedding_raw.get("reindex_required") is not None
                else None
            ),
            indexed_model_keys=[
                str(item) for item in (embedding_raw.get("indexed_model_keys") or [])
            ],
            indexed_dimensions=[
                int(item) for item in (embedding_raw.get("indexed_dimensions") or [])
            ],
            detail=(
                str(embedding_raw["detail"]) if embedding_raw.get("detail") is not None else None
            ),
        ),
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


@router.get(
    "/system/models",
    response_model=SystemModelsCatalogDTO,
    responses={
        200: {"description": "LLM model inventory"},
        503: {"description": "Application container not ready"},
    },
    summary="LLM model inventory (developer)",
    tags=["health"],
)
async def system_models(settings: SettingsDep, response: Response) -> SystemModelsCatalogDTO:
    """Return selected / installed LLM models without calling GenerationService."""
    from rag_enterprise.core.dependencies.providers import get_container
    from rag_enterprise.generation.providers import describe_llm_runtime

    try:
        container = get_container()
        provider = container.llm_provider if container.is_initialized else None
    except RuntimeError:
        container = None
        provider = None
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    info = describe_llm_runtime(settings, provider)
    inventory = None
    if provider is not None and hasattr(provider, "models_inventory"):
        inventory = provider.models_inventory()  # type: ignore[attr-defined]

    if inventory is None:
        inventory = {
            "backend": info.backend,
            "provider": info.provider,
            "selection_mode": info.selection_mode,
            "selected_model": info.selected_model or info.model,
            "installed_models": list(info.installed_models),
            "base_url": info.base_url,
            "reachable": info.reachability == "reachable",
            "ollama_version": info.ollama_version,
            "detail": info.detail,
        }

    return SystemModelsCatalogDTO(
        backend=str(inventory.get("backend") or info.backend),
        provider=str(inventory.get("provider") or info.provider),
        selection_mode=(
            str(inventory["selection_mode"])
            if inventory.get("selection_mode") is not None
            else None
        ),
        selected_model=(
            str(inventory["selected_model"])
            if inventory.get("selected_model") is not None
            else None
        ),
        installed_models=[str(item) for item in (inventory.get("installed_models") or [])],
        base_url=str(inventory["base_url"]) if inventory.get("base_url") is not None else None,
        reachable=bool(inventory["reachable"]) if inventory.get("reachable") is not None else None,
        ollama_version=(
            str(inventory["ollama_version"])
            if inventory.get("ollama_version") is not None
            else None
        ),
        detail=str(inventory["detail"]) if inventory.get("detail") is not None else None,
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
