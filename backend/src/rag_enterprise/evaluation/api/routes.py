"""Thin HTTP read adapters over Feature 007 filesystem evaluation artifacts."""

from __future__ import annotations

import asyncio
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Query, status

from rag_enterprise.api.common.errors import ApplicationException
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.application.common import ApplicationError, ErrorCode
from rag_enterprise.evaluation.api.dependencies import EvaluationServiceDep
from rag_enterprise.evaluation.api.schemas import (
    EvaluationDatasetListDTO,
    EvaluationRunDetailDTO,
    EvaluationRunListDTO,
    EvaluationRunSummaryDTO,
)
from rag_enterprise.knowledge.api.dependencies import ActorDep

router = APIRouter(prefix="/workspaces/{workspace_id}/evaluations", tags=["evaluation"])


@router.get(
    "/runs",
    response_model=SuccessEnvelope[EvaluationRunListDTO],
    status_code=status.HTTP_200_OK,
)
async def list_evaluation_runs(
    workspace_id: uuid.UUID,
    actor: ActorDep,
    service: EvaluationServiceDep,
    knowledge_base_id: Annotated[uuid.UUID | None, Query()] = None,
    dataset_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
) -> SuccessEnvelope[EvaluationRunListDTO]:
    """List offline evaluation runs from filesystem artifacts."""
    _ = actor
    raw_items = await asyncio.to_thread(
        service.list_runs,
        workspace_id=workspace_id,
        knowledge_base_id=knowledge_base_id,
        dataset_id=dataset_id,
        limit=limit,
    )
    items = [EvaluationRunSummaryDTO.model_validate(item) for item in raw_items]
    return success_response(EvaluationRunListDTO(items=items))


@router.get(
    "/runs/{run_id}",
    response_model=SuccessEnvelope[EvaluationRunDetailDTO],
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_run(
    workspace_id: uuid.UUID,
    run_id: str,
    actor: ActorDep,
    service: EvaluationServiceDep,
) -> SuccessEnvelope[EvaluationRunDetailDTO]:
    """Return config, summary, and metrics for one evaluation run."""
    _ = actor
    try:
        payload = await asyncio.to_thread(
            service.get_run,
            workspace_id=workspace_id,
            run_id=run_id,
        )
    except FileNotFoundError as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message="Evaluation run not found",
                details={"run_id": run_id},
            )
        ) from exc
    except (OSError, ValueError) as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Unable to load evaluation artifacts",
                details={"run_id": run_id, "reason": str(exc)},
            )
        ) from exc

    return success_response(EvaluationRunDetailDTO.model_validate(payload))


@router.get(
    "/runs/{run_id}/metrics",
    response_model=SuccessEnvelope[dict[str, Any]],
    status_code=status.HTTP_200_OK,
)
async def get_evaluation_metrics(
    workspace_id: uuid.UUID,
    run_id: str,
    actor: ActorDep,
    service: EvaluationServiceDep,
) -> SuccessEnvelope[dict[str, Any]]:
    """Return metrics.json for one evaluation run."""
    _ = actor
    try:
        payload = await asyncio.to_thread(
            service.get_run,
            workspace_id=workspace_id,
            run_id=run_id,
        )
    except FileNotFoundError as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.NOT_FOUND,
                message="Evaluation run not found",
                details={"run_id": run_id},
            )
        ) from exc
    except (OSError, ValueError) as exc:
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Unable to load evaluation artifacts",
                details={"run_id": run_id, "reason": str(exc)},
            )
        ) from exc

    metrics = payload["metrics"]
    if not isinstance(metrics, dict):
        raise ApplicationException(
            ApplicationError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Corrupt metrics artifact",
                details={"run_id": run_id},
            )
        )
    return success_response(metrics)


@router.get(
    "/datasets",
    response_model=SuccessEnvelope[EvaluationDatasetListDTO],
    status_code=status.HTTP_200_OK,
)
async def list_evaluation_datasets(
    workspace_id: uuid.UUID,
    actor: ActorDep,
    service: EvaluationServiceDep,
) -> SuccessEnvelope[EvaluationDatasetListDTO]:
    """List dataset ids observed in stored evaluation runs."""
    _ = actor
    items = await asyncio.to_thread(service.list_dataset_ids, workspace_id=workspace_id)
    return success_response(EvaluationDatasetListDTO(items=items))
