"""Operational readiness and system inventory checks (RC1.2).

Does not call LLM or embedding providers. Fast dependency probes only.
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
from rag_enterprise.indexing.models import Chunk, Embedding
from rag_enterprise.knowledge.models import Document

READY_CHECK_TIMEOUT_SECONDS = 2.0
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

    ready = all(item.ok for item in checks)
    return ReadinessReport(ready=ready, checks=tuple(checks))


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
    return CheckResult(name="upload_storage", ok=True, detail="put/get/delete ok")


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

    return {
        "version": __version__,
        "environment": settings.app_env,
        "providers": {
            "llm": {
                "name": "openai_compatible",
                "mode": settings.llm_backend,
            },
            "embedding": {
                "name": "bge_m3",
                "mode": settings.embedding_backend,
            },
        },
        "models": {
            "llm_model_key": settings.llm_model_key,
            "embedding_model_key": settings.embedding_model_key,
            "embedding_dimensions": settings.embedding_dimensions,
            "prompt_template_version": "v1",
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
