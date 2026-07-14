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

    def list_runs(
        self,
        *,
        workspace_id: uuid.UUID,
        knowledge_base_id: uuid.UUID | None = None,
        dataset_id: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, object]]:
        """List experiment run previews from filesystem artifacts (read-only)."""
        items: list[dict[str, object]] = []
        for experiment_id in self._storage.list_experiment_ids():
            config_path = self._storage.experiment_dir(experiment_id) / "config.json"
            summary_path = self._storage.experiment_dir(experiment_id) / "summary.json"
            metrics_path = self._storage.experiment_dir(experiment_id) / "metrics.json"
            if not config_path.exists() or not summary_path.exists():
                continue
            try:
                config = self._storage.read_config(experiment_id)
                summary = self._storage.read_summary(experiment_id)
                metrics_payload = (
                    self._storage.read_metrics(experiment_id) if metrics_path.exists() else None
                )
            except (OSError, ValueError, KeyError):
                continue
            if config.workspace_id != workspace_id:
                continue
            if knowledge_base_id is not None and config.knowledge_base_id != knowledge_base_id:
                continue
            if dataset_id is not None and config.dataset_id != dataset_id:
                continue
            retrieval = (
                metrics_payload.get("metrics", {}).get("retrieval", {})
                if isinstance(metrics_payload, dict)
                else {}
            )
            generation = (
                metrics_payload.get("metrics", {}).get("generation", {})
                if isinstance(metrics_payload, dict)
                else {}
            )
            latency = (
                metrics_payload.get("metrics", {}).get("latency_ms", {})
                if isinstance(metrics_payload, dict)
                else {}
            )
            items.append(
                {
                    "run_id": experiment_id,
                    "name": config.name,
                    "status": summary.status.value
                    if hasattr(summary.status, "value")
                    else str(summary.status),
                    "knowledge_base_id": str(config.knowledge_base_id),
                    "dataset_id": config.dataset_id,
                    "dataset_version": config.dataset_version,
                    "created_at": config.created_at.isoformat() if config.created_at else None,
                    "top_k": config.top_k,
                    "prompt_version": config.prompt_version,
                    "llm": config.llm,
                    "failing_metrics": list(summary.failing_metrics),
                    "question_count": summary.question_count,
                    "error_count": summary.error_count,
                    "recall_at_k": retrieval.get("recall_at_k")
                    if isinstance(retrieval, dict)
                    else None,
                    "mrr": retrieval.get("mrr") if isinstance(retrieval, dict) else None,
                    "groundedness": generation.get("groundedness")
                    if isinstance(generation, dict)
                    else None,
                    "citation_accuracy": generation.get("citation_accuracy")
                    if isinstance(generation, dict)
                    else None,
                    "citation_precision_mean": generation.get("citation_precision_mean")
                    if isinstance(generation, dict)
                    else None,
                    "abstention_precision": generation.get("abstention_precision")
                    if isinstance(generation, dict)
                    else None,
                    "retrieval_latency_mean_ms": latency.get("retrieval_mean")
                    if isinstance(latency, dict)
                    else None,
                    "e2e_p95_ms": latency.get("e2e_p95") if isinstance(latency, dict) else None,
                    "e2e_p50_ms": latency.get("e2e_p50") if isinstance(latency, dict) else None,
                    "e2e_mean_ms": latency.get("e2e_mean") if isinstance(latency, dict) else None,
                }
            )
            if len(items) >= limit:
                break

        def sort_key(item: dict[str, object]) -> str:
            created = item.get("created_at")
            return str(created) if created is not None else ""

        items.sort(key=sort_key, reverse=True)
        return items[:limit]

    def get_run(self, *, workspace_id: uuid.UUID, run_id: str) -> dict[str, object]:
        """Load one run's config + summary + metrics for a workspace."""
        if not self._storage.exists(run_id):
            raise FileNotFoundError(run_id)
        config = self._storage.read_config(run_id)
        if config.workspace_id != workspace_id:
            raise FileNotFoundError(run_id)
        summary = self._storage.read_summary(run_id)
        metrics_payload = self._storage.read_metrics(run_id)
        return {
            "run_id": run_id,
            "config": config.model_dump(mode="json"),
            "summary": summary.model_dump(mode="json"),
            "metrics": metrics_payload,
        }

    def list_dataset_ids(self, *, workspace_id: uuid.UUID) -> list[str]:
        """Distinct dataset ids observed in completed runs for a workspace."""
        seen: set[str] = set()
        for item in self.list_runs(workspace_id=workspace_id, limit=500):
            dataset_id = item.get("dataset_id")
            if isinstance(dataset_id, str) and dataset_id:
                seen.add(dataset_id)
        return sorted(seen)
