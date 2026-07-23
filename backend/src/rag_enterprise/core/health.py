"""Operational readiness and system inventory checks (RC1.2 / RC2.7).

Database and storage probes remain fast. When ``LLM_BACKEND=local``, readiness
also probes the configured LLM provider through the factory surface.
"""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import func, select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise import __version__
from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.core.config.settings import Settings
from rag_enterprise.core.dependencies.providers import AppContainer, get_container
from rag_enterprise.core.runtime import is_configuration_validated
from rag_enterprise.generation.providers import describe_llm_runtime, probe_llm_provider
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.indexing.providers import (
    describe_embedding_runtime,
    probe_embedding_provider,
)
from rag_enterprise.knowledge.models import Document

READY_CHECK_TIMEOUT_SECONDS = 2.0
LLM_READY_CHECK_TIMEOUT_SECONDS = 30.0
EMBEDDING_READY_CHECK_TIMEOUT_SECONDS = 180.0
UPLOAD_PROBE_KEY = "__health__/ready-probe"


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single readiness dependency check."""

    name: str
    ok: bool
    detail: str


@dataclass(frozen=True)
class ReadinessReport:
    """Aggregated readiness result."""

    ready: bool
    checks: tuple[CheckResult, ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.ready else "not_ready",
            "checks": [
                {"name": item.name, "ok": item.ok, "detail": item.detail} for item in self.checks
            ],
        }


async def evaluate_readiness(settings: Settings) -> ReadinessReport:
    """Run fast dependency checks for the readiness probe."""
    checks: list[CheckResult] = []

    config_ok = is_configuration_validated()
    checks.append(
        CheckResult(
            name="configuration",
            ok=config_ok,
            detail="validated at startup" if config_ok else "configuration not validated",
        )
    )

    container, di_ok, di_detail = _resolve_container()
    checks.append(CheckResult(name="dependency_injection", ok=di_ok, detail=di_detail))

    if container is None or not di_ok:
        checks.append(
            CheckResult(
                name="database",
                ok=False,
                detail="skipped: DI not initialized",
            )
        )
        checks.append(
            CheckResult(
                name="evaluation_storage",
                ok=False,
                detail="skipped: DI not initialized",
            )
        )
        checks.append(
            CheckResult(
                name="upload_storage",
                ok=False,
                detail="skipped: DI not initialized",
            )
        )
        if settings.llm_backend == "local":
            checks.append(
                CheckResult(
                    name="llm",
                    ok=False,
                    detail="skipped: DI not initialized",
                )
            )
        return ReadinessReport(ready=False, checks=tuple(checks))

    db_result = await _check_database(container.engine)
    checks.append(db_result)

    eval_result = await asyncio.to_thread(
        _check_evaluation_storage,
        settings.evaluation_storage_root,
    )
    checks.append(eval_result)

    upload_result = await _check_upload_storage(container.file_storage)
    checks.append(upload_result)

    if settings.llm_backend == "local" and container.llm_provider is not None:
        checks.append(await _check_local_llm(container.llm_provider))

    if container.embedding_provider is not None:
        checks.append(await _check_embedding_provider(container.embedding_provider))
        if container.session_factory is not None:
            alignment = await _refresh_embedding_index_alignment(container)
            checks.append(_check_embedding_index(alignment))

    ready = all(item.ok for item in checks)
    return ReadinessReport(ready=ready, checks=tuple(checks))


async def _refresh_embedding_index_alignment(container: AppContainer) -> dict[str, object]:
    """Re-check DB vectors vs live provider (schema may appear after startup)."""
    from rag_enterprise.indexing.providers import check_index_embedding_alignment

    assert container.session_factory is not None
    assert container.embedding_provider is not None
    try:
        alignment = await check_index_embedding_alignment(
            container.session_factory,
            container.embedding_provider,
            container.settings,
        )
    except Exception as exc:  # noqa: BLE001 — readiness must not crash
        alignment = {
            "compatible": False,
            "reindex_required": True,
            "indexed_model_keys": [],
            "indexed_dimensions": [],
            "detail": f"index alignment check failed: {exc}",
            "sample_cosine": None,
        }
    container.embedding_index_alignment = alignment
    return alignment


async def _check_local_llm(provider: object) -> CheckResult:
    try:
        snapshot = await asyncio.wait_for(
            probe_llm_provider(provider),  # type: ignore[arg-type]
            timeout=LLM_READY_CHECK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return CheckResult(
            name="llm",
            ok=False,
            detail="local LLM readiness probe timed out",
        )
    except Exception as exc:  # noqa: BLE001 — surface as not-ready, never crash probe
        return CheckResult(name="llm", ok=False, detail=f"local LLM probe error: {exc}")

    if snapshot is None:
        return CheckResult(
            name="llm",
            ok=False,
            detail="local LLM provider does not support health probes",
        )

    ok = bool(snapshot.get("reachable")) and snapshot.get("detail") == "ok"
    installed = snapshot.get("installed_models") or []
    detail = (
        f"reachable={snapshot.get('reachable')} "
        f"selected_model={snapshot.get('selected_model')} "
        f"installed_models={list(installed)} "
        f"response_time_ms={snapshot.get('response_time_ms')} "
        f"detail={snapshot.get('detail')}"
    )
    return CheckResult(name="llm", ok=ok, detail=detail)


async def _check_embedding_provider(provider: object) -> CheckResult:
    try:
        snapshot = await asyncio.wait_for(
            probe_embedding_provider(provider),  # type: ignore[arg-type]
            timeout=EMBEDDING_READY_CHECK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return CheckResult(
            name="embedding",
            ok=False,
            detail="embedding readiness probe timed out",
        )
    except Exception as exc:  # noqa: BLE001 — surface as not-ready, never crash probe
        return CheckResult(name="embedding", ok=False, detail=f"embedding probe error: {exc}")

    ok = bool(snapshot.get("ok")) and snapshot.get("detail") == "ok"
    dims_match = snapshot.get("model_dimensions") == snapshot.get("vector_dimensions")
    ok = ok and bool(dims_match)
    detail = (
        f"provider={snapshot.get('backend_provider')} "
        f"loaded_model={snapshot.get('loaded_model')} "
        f"model_dimensions={snapshot.get('model_dimensions')} "
        f"vector_dimensions={snapshot.get('vector_dimensions')} "
        f"loaded={snapshot.get('loaded')} "
        f"detail={snapshot.get('detail')}"
    )
    return CheckResult(name="embedding", ok=ok, detail=detail)


def _check_embedding_index(alignment: dict[str, object]) -> CheckResult:
    """Warn operators when stored vectors were not produced by the live provider."""
    reindex_required = bool(alignment.get("reindex_required"))
    compatible = alignment.get("compatible")
    detail = str(alignment.get("detail") or "unknown")
    # Deferred / unknown (compatible is None) is not a hard failure.
    if compatible is None and not reindex_required:
        return CheckResult(name="embedding_index", ok=True, detail=detail)
    ok = compatible is True and not reindex_required
    return CheckResult(name="embedding_index", ok=ok, detail=detail)


def _resolve_container() -> tuple[AppContainer | None, bool, str]:
    try:
        container = get_container()
    except RuntimeError:
        return None, False, "application container is not available"
    if not container.is_initialized:
        return container, False, "application container is not initialized"
    return container, True, "initialized"


async def _check_database(engine: AsyncEngine | None) -> CheckResult:
    if engine is None:
        return CheckResult(name="database", ok=False, detail="engine is not configured")
    try:
        await asyncio.wait_for(_ping_database(engine), timeout=READY_CHECK_TIMEOUT_SECONDS)
    except TimeoutError:
        return CheckResult(
            name="database",
            ok=False,
            detail=f"connectivity timed out after {READY_CHECK_TIMEOUT_SECONDS:.0f}s",
        )
    except SQLAlchemyError as exc:
        return CheckResult(name="database", ok=False, detail=f"connectivity failed: {exc}")
    except OSError as exc:
        return CheckResult(name="database", ok=False, detail=f"connectivity failed: {exc}")
    return CheckResult(name="database", ok=True, detail="connectivity ok")


async def _ping_database(engine: AsyncEngine) -> None:
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


def _check_evaluation_storage(root: str) -> CheckResult:
    path = Path(root)
    if not path.exists() or not path.is_dir():
        return CheckResult(
            name="evaluation_storage",
            ok=False,
            detail=f"directory missing: {path}",
        )
    probe = path / ".ready_probe"
    try:
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return CheckResult(
            name="evaluation_storage",
            ok=False,
            detail=f"not writable: {exc}",
        )
    return CheckResult(name="evaluation_storage", ok=True, detail="directory available")


async def _check_upload_storage(storage: FileStorage | None) -> CheckResult:
    if storage is None:
        return CheckResult(name="upload_storage", ok=False, detail="file storage is not configured")
    org_id = uuid.UUID("018f0000-0000-7000-8000-0000000000a1")
    workspace_id = uuid.UUID("018f0000-0000-7000-8000-0000000000a2")
    try:
        await asyncio.wait_for(
            _probe_upload_storage(storage, org_id=org_id, workspace_id=workspace_id),
            timeout=READY_CHECK_TIMEOUT_SECONDS,
        )
    except TimeoutError:
        return CheckResult(
            name="upload_storage",
            ok=False,
            detail=f"probe timed out after {READY_CHECK_TIMEOUT_SECONDS:.0f}s",
        )
    except (OSError, KeyError, RuntimeError, TypeError, ValueError) as exc:
        return CheckResult(name="upload_storage", ok=False, detail=f"probe failed: {exc}")
    return CheckResult(
        name="upload_storage",
        ok=True,
        detail="filesystem put/get/delete ok",
    )


async def _probe_upload_storage(
    storage: FileStorage,
    *,
    org_id: uuid.UUID,
    workspace_id: uuid.UUID,
) -> None:
    await storage.put(
        organization_id=org_id,
        workspace_id=workspace_id,
        key=UPLOAD_PROBE_KEY,
        data=b"ready",
        content_type="text/plain",
    )
    payload = await storage.get(key=UPLOAD_PROBE_KEY)
    if payload != b"ready":
        raise RuntimeError("upload storage probe returned unexpected payload")
    await storage.delete(key=UPLOAD_PROBE_KEY)


async def build_system_inventory(settings: Settings) -> dict[str, Any]:
    """Collect process/config inventory and lightweight DB/eval counts."""
    container, di_ok, _ = _resolve_container()
    document_count = 0
    chunk_count = 0
    embedding_count = 0
    evaluation_run_count = 0
    counts_ok = False
    counts_detail = "DI not initialized"

    if container is not None and di_ok and container.session_factory is not None:
        try:
            document_count, chunk_count, embedding_count = await asyncio.wait_for(
                _count_entities(container.session_factory),
                timeout=READY_CHECK_TIMEOUT_SECONDS,
            )
            counts_ok = True
            counts_detail = "ok"
        except TimeoutError:
            counts_detail = "count query timed out"
        except SQLAlchemyError as exc:
            counts_detail = f"count query failed: {exc}"

    if container is not None and container.evaluation_service is not None:
        try:
            evaluation_run_count = len(
                await asyncio.to_thread(container.evaluation_service.storage.list_experiment_ids)
            )
        except OSError:
            evaluation_run_count = 0

    llm = describe_llm_runtime(settings, container.llm_provider if container else None)
    if (
        container is not None
        and di_ok
        and container.embedding_provider is not None
        and container.session_factory is not None
    ):
        await _refresh_embedding_index_alignment(container)
    embedding = describe_embedding_runtime(
        settings,
        container.embedding_provider if container else None,
        index_alignment=(
            container.embedding_index_alignment
            if container is not None and container.embedding_index_alignment is not None
            else None
        ),
    )
    return {
        "version": __version__,
        "environment": settings.app_env,
        "providers": {
            "llm": {
                "name": llm.provider,
                "mode": llm.backend,
                "backend": llm.backend,
                "provider": llm.provider,
                "model": llm.selected_model or llm.model,
                "timeout_seconds": llm.timeout_seconds,
                "reachability": llm.reachability,
                "latency_ms": llm.latency_ms,
            },
            "embedding": {
                "name": embedding.provider,
                "mode": embedding.backend,
                "backend": embedding.backend,
                "provider": embedding.provider,
                "model": embedding.model,
                "dimensions": embedding.dimensions,
                "loaded": embedding.loaded,
                "index_compatible": embedding.index_compatible,
                "reindex_required": embedding.reindex_required,
            },
        },
        "models": {
            "llm_model_key": settings.llm_model_key,
            "embedding_model_key": settings.embedding_model_key,
            "embedding_dimensions": settings.embedding_dimensions,
            "prompt_template_version": "v1",
        },
        "llm": {
            "backend": llm.backend,
            "provider": llm.provider,
            "model": llm.selected_model or llm.model,
            "selected_model": llm.selected_model or llm.model,
            "installed_models": list(llm.installed_models),
            "timeout_seconds": llm.timeout_seconds,
            "ollama_version": llm.ollama_version,
            "selection_mode": llm.selection_mode,
            "reachability": llm.reachability,
        },
        "embedding": {
            "backend": embedding.backend,
            "provider": embedding.provider,
            "model": embedding.model,
            "dimensions": embedding.dimensions,
            "loaded": embedding.loaded,
            "index_compatible": embedding.index_compatible,
            "reindex_required": embedding.reindex_required,
            "indexed_model_keys": list(embedding.indexed_model_keys),
            "indexed_dimensions": list(embedding.indexed_dimensions),
            "detail": embedding.detail,
        },
        "counts": {
            "documents": document_count,
            "chunks": chunk_count,
            "embeddings": embedding_count,
            "evaluation_runs": evaluation_run_count,
            "ok": counts_ok,
            "detail": counts_detail,
        },
        "configuration_validated": is_configuration_validated(),
        "dependency_injection_initialized": di_ok,
    }


async def _count_entities(
    session_factory: async_sessionmaker[AsyncSession],
) -> tuple[int, int, int]:
    async with session_factory() as session:
        documents = await session.scalar(select(func.count()).select_from(Document))
        chunks = await session.scalar(select(func.count()).select_from(Chunk))
        embeddings = await session.scalar(select(func.count()).select_from(Embedding))
    return int(documents or 0), int(chunks or 0), int(embeddings or 0)
