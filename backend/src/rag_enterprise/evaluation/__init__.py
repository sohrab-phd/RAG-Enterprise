"""Offline RAG evaluation framework (Feature 007)."""

from rag_enterprise.evaluation.dataset import load_dataset
from rag_enterprise.evaluation.exceptions import (
    AggregateIncompleteError,
    DatasetNotFoundError,
    DatasetValidationError,
    EvaluationError,
    KnowledgeBaseUnavailableError,
)
from rag_enterprise.evaluation.models import (
    EvaluationStatus,
    EvaluationSummary,
    ExperimentConfig,
    ExperimentThresholds,
    GoldenDataset,
)
from rag_enterprise.evaluation.service import EvaluationService
from rag_enterprise.evaluation.storage import ExperimentStorage

__all__ = [
    "AggregateIncompleteError",
    "DatasetNotFoundError",
    "DatasetValidationError",
    "EvaluationError",
    "EvaluationService",
    "EvaluationStatus",
    "EvaluationSummary",
    "ExperimentConfig",
    "ExperimentStorage",
    "ExperimentThresholds",
    "GoldenDataset",
    "KnowledgeBaseUnavailableError",
    "load_dataset",
]
