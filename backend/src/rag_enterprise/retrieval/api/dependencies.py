"""Retrieval API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.retrieval.service import RetrievalService


def get_retrieval_service() -> RetrievalService:
    container = get_container()
    if container.retrieval_service is None:
        raise RuntimeError("Retrieval service is not initialized")
    return container.retrieval_service


RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
