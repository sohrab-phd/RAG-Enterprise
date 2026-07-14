"""Filesystem persistence for evaluation experiment artifacts."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rag_enterprise.evaluation.models import (
    EvaluationSummary,
    ExperimentConfig,
    MetricsReport,
    QuestionOutcome,
)


class ExperimentStorage:
    """Persist experiment config, per-question results, and aggregate metrics."""

    def __init__(self, root: Path | str) -> None:
        self._root = Path(root)

    @property
    def root(self) -> Path:
        return self._root

    def experiment_dir(self, experiment_id: str) -> Path:
        return self._root / "experiments" / experiment_id

    def ensure_dir(self, experiment_id: str) -> Path:
        path = self.experiment_dir(experiment_id)
        path.mkdir(parents=True, exist_ok=True)
        return path

    def write_config(self, config: ExperimentConfig) -> Path:
        directory = self.ensure_dir(config.experiment_id)
        path = directory / "config.json"
        path.write_text(
            json.dumps(config.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def write_results(self, experiment_id: str, outcomes: list[QuestionOutcome]) -> Path:
        directory = self.ensure_dir(experiment_id)
        path = directory / "results.jsonl"
        lines = [
            json.dumps(outcome.model_dump(mode="json"), sort_keys=True) for outcome in outcomes
        ]
        path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")
        return path

    def write_metrics(self, experiment_id: str, report: MetricsReport) -> Path:
        directory = self.ensure_dir(experiment_id)
        path = directory / "metrics.json"
        payload = {
            "dataset_id": report.dataset_id,
            "dataset_version": report.dataset_version,
            "experiment_id": report.experiment_id,
            "metrics": {
                "retrieval": report.retrieval.model_dump(mode="json"),
                "generation": report.generation.model_dump(mode="json"),
                "latency_ms": report.latency_ms.model_dump(mode="json"),
                "tokens": report.tokens.model_dump(mode="json"),
            },
            "by_language": report.by_language,
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
        return path

    def write_summary(self, summary: EvaluationSummary) -> Path:
        directory = self.ensure_dir(summary.experiment_id)
        path = directory / "summary.json"
        path.write_text(
            json.dumps(summary.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def read_config(self, experiment_id: str) -> ExperimentConfig:
        path = self.experiment_dir(experiment_id) / "config.json"
        payload = json.loads(path.read_text(encoding="utf-8"))
        return ExperimentConfig.model_validate(payload)

    def read_results(self, experiment_id: str) -> list[QuestionOutcome]:
        path = self.experiment_dir(experiment_id) / "results.jsonl"
        outcomes: list[QuestionOutcome] = []
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if not line.strip():
                continue
            outcomes.append(QuestionOutcome.model_validate(json.loads(line)))
        return outcomes

    def read_metrics(self, experiment_id: str) -> dict[str, Any]:
        path = self.experiment_dir(experiment_id) / "metrics.json"
        payload: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
        return payload

    def read_summary(self, experiment_id: str) -> EvaluationSummary:
        path = self.experiment_dir(experiment_id) / "summary.json"
        return EvaluationSummary.model_validate(json.loads(path.read_text(encoding="utf-8")))
