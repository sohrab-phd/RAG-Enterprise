"""Generation API dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends

from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.generation.service import GenerationService


def get_generation_service() -> GenerationService:
    container = get_container()
    if container.generation_service is None:
        raise RuntimeError("Generation service is not initialized")
    return container.generation_service


GenerationServiceDep = Annotated[GenerationService, Depends(get_generation_service)]
