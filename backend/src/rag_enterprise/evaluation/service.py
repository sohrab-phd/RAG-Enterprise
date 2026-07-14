"""Offline evaluation service facade."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import Path

from rag_enterprise.evaluation.dataset import load_dataset
from rag_enterprise.evaluation.models import (
    EvaluationSummary,
    ExperimentConfig,
    ExperimentThresholds,
    GoldenDataset,
)
from rag_enterprise.evaluation.runner import ExperimentRunner, GenerationCaller, RetrievalCaller
from rag_enterprise.evaluation.storage import ExperimentStorage


class EvaluationService:
    """Load datasets and run offline RAG evaluation experiments."""

    def __init__(
        self,
        *,
        retrieval_service: RetrievalCaller,
        generation_service: GenerationCaller,
        storage_root: Path | str,
    ) -> None:
        self._storage = ExperimentStorage(storage_root)
        self._runner = ExperimentRunner(
            retrieval_service=retrieval_service,
            generation_service=generation_service,
            storage=self._storage,
        )

    @property
    def storage(self) -> ExperimentStorage:
        return self._storage

    def load_dataset(self, directory: Path | str) -> GoldenDataset:
        """Validate and load a versioned golden dataset directory."""
        return load_dataset(directory)

    def create_config(
        self,
        *,
        name: str,
        organization_id: uuid.UUID,
        workspace_id: uuid.UUID,
        user_id: uuid.UUID,
        knowledge_base_id: uuid.UUID,
        dataset_id: str,
        dataset_version: str,
        dataset_path: str,
        embedding_model: str = "BAAI/bge-m3",
        chunk_size: int = 1000,
        overlap: int = 125,
        top_k: int = 8,
        prompt_version: str = "v1",
        llm: str = "gpt-4o-mini",
        min_evidence_score: float = 0.25,
        max_history_messages: int = 0,
        thresholds: ExperimentThresholds | None = None,
        experiment_id: str | None = None,
        permissions: frozenset[str] | None = None,
    ) -> ExperimentConfig:
        """Build an immutable experiment configuration snapshot."""
        return ExperimentConfig(
            experiment_id=experiment_id or str(uuid.uuid4()),
            name=name,
            organization_id=organization_id,
            workspace_id=workspace_id,
            user_id=user_id,
            knowledge_base_id=knowledge_base_id,
            dataset_id=dataset_id,
            dataset_version=dataset_version,
            dataset_path=dataset_path,
            embedding_model=embedding_model,
            chunk_size=chunk_size,
            overlap=overlap,
            top_k=top_k,
            prompt_version=prompt_version,
            llm=llm,
            min_evidence_score=min_evidence_score,
            max_history_messages=max_history_messages,
            thresholds=thresholds or ExperimentThresholds(),
            permissions=permissions
            or frozenset(
                {
                    "knowledge_base:read",
                    "document:read",
                    "organization:evaluation:manage",
                }
            ),
            created_at=datetime.now(UTC),
            created_by_user_id=user_id,
        )

    async def run(self, config: ExperimentConfig) -> EvaluationSummary:
        """Execute an experiment and persist filesystem artifacts."""
        return await self._runner.run(config)
