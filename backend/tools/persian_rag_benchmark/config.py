"""CLI / run configuration for the Persian RAG benchmark."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ORG_ID = uuid.UUID("018f0000-0000-7000-8000-000000000001")
DEFAULT_WORKSPACE_ID = uuid.UUID("018f0000-0000-7000-8000-000000000002")
DEFAULT_USER_ID = uuid.UUID("018f0000-0000-7000-8000-000000000003")

DEFAULT_PERMISSIONS: frozenset[str] = frozenset(
    {
        "knowledge_base:read",
        "document:read",
        "document:create",
        "document:update",
        "organization:evaluation:manage",
    }
)


@dataclass(frozen=True)
class BenchmarkConfig:
    """Immutable run configuration for one benchmark execution."""

    organization_id: uuid.UUID = DEFAULT_ORG_ID
    workspace_id: uuid.UUID = DEFAULT_WORKSPACE_ID
    user_id: uuid.UUID = DEFAULT_USER_ID
    knowledge_base_id: uuid.UUID | None = None
    document_ids: tuple[uuid.UUID, ...] = ()
    output_dir: Path = field(default_factory=lambda: Path("benchmark-artifacts") / "persian-rag")
    # Curated Feature-007 gold (required for Measured retrieval metrics).
    curated_dataset_path: Path | None = None
    # Optional circular probe generation (never counted as Measured retrieval).
    enable_auto_corpus_probes: bool = False
    top_k: int = 8
    questions_per_document_min: int = 40
    questions_per_document_max: int = 60
    max_robustness_variants_per_question: int = 8
    include_generation: bool = True
    include_embedding_diagnostics: bool = True
    include_chunk_diagnostics: bool = True
    dataset_only: bool = False
    seed: int = 42
    permissions: frozenset[str] = DEFAULT_PERMISSIONS
    run_name: str = "persian-rag-v1"

    def resolve_output_dir(self) -> Path:
        path = self.output_dir
        path.mkdir(parents=True, exist_ok=True)
        return path
