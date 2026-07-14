"""Evaluation API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.evaluation.service import EvaluationService


def get_evaluation_service() -> EvaluationService:
    container = get_container()
    if container.evaluation_service is None:
        raise RuntimeError("Evaluation service is not initialized")
    return container.evaluation_service


EvaluationServiceDep = Annotated[EvaluationService, Depends(get_evaluation_service)]
