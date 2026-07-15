"""CLI entrypoint for the Persian RAG Diagnostics & Benchmark Framework."""

from __future__ import annotations

import argparse
import asyncio
import json
import uuid
from pathlib import Path

from tools.persian_rag_benchmark.config import (
    DEFAULT_ORG_ID,
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    BenchmarkConfig,
)
from tools.persian_rag_benchmark.orchestrator import run_benchmark


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="persian_rag_benchmark",
        description=(
            "Developer-only Persian RAG diagnostics & benchmark. "
            "Measured retrieval metrics require curated external gold (--dataset-path)."
        ),
    )
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--organization-id", default=str(DEFAULT_ORG_ID))
    parser.add_argument("--workspace-id", default=str(DEFAULT_WORKSPACE_ID))
    parser.add_argument("--user-id", default=str(DEFAULT_USER_ID))
    parser.add_argument("--document-id", action="append", default=[])
    parser.add_argument(
        "--dataset-path",
        default=None,
        help=(
            "Curated Feature-007 dataset file or directory (dataset.jsonl / "
            "evaluation.jsonl). Required for Measured Hit@k/Recall@k/Precision@k/MRR."
        ),
    )
    parser.add_argument(
        "--enable-auto-corpus-probes",
        action="store_true",
        help=(
            "Also generate circular corpus probes (excluded from Measured retrieval "
            "metrics). Alone without --dataset-path runs probes only."
        ),
    )
    parser.add_argument("--output-dir", default="benchmark-artifacts/persian-rag")
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--questions-min", type=int, default=40)
    parser.add_argument("--questions-max", type=int, default=60)
    parser.add_argument("--robustness-variants", type=int, default=8)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--run-name", default="persian-rag-v1")
    parser.add_argument("--dataset-only", action="store_true")
    parser.add_argument("--skip-generation", action="store_true")
    parser.add_argument("--skip-embeddings", action="store_true")
    parser.add_argument("--skip-chunks", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    curated = Path(args.dataset_path) if args.dataset_path else None
    config = BenchmarkConfig(
        organization_id=uuid.UUID(args.organization_id),
        workspace_id=uuid.UUID(args.workspace_id),
        user_id=uuid.UUID(args.user_id),
        knowledge_base_id=uuid.UUID(args.knowledge_base_id),
        document_ids=tuple(uuid.UUID(value) for value in args.document_id),
        curated_dataset_path=curated,
        enable_auto_corpus_probes=args.enable_auto_corpus_probes,
        output_dir=Path(args.output_dir),
        top_k=args.top_k,
        questions_per_document_min=args.questions_min,
        questions_per_document_max=args.questions_max,
        max_robustness_variants_per_question=args.robustness_variants,
        include_generation=not args.skip_generation,
        include_embedding_diagnostics=not args.skip_embeddings,
        include_chunk_diagnostics=not args.skip_chunks,
        dataset_only=args.dataset_only,
        seed=args.seed,
        run_name=args.run_name,
    )
    summary = asyncio.run(run_benchmark(config))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
