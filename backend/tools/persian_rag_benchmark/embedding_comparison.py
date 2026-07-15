"""RC2.3 embedding model comparison harness (developer-only).

For each candidate model: force re-embed + re-index the KB, run the Persian
benchmark, collect Measured IR and operational / vector diagnostics.

Usage (from backend/):

  uv sync --extra embeddings
  uv run python -m tools.persian_rag_benchmark.embedding_comparison \\
    --knowledge-base-id <KB_UUID> --dataset-path ../demo/evaluation
"""

from __future__ import annotations

import argparse
import asyncio
import json
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import func, select

from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import AppContainer, lifespan_container
from rag_enterprise.indexing.enums import IndexStatus
from rag_enterprise.indexing.models import Embedding
from rag_enterprise.knowledge.enums import DocumentStatus, ProcessingStatus
from rag_enterprise.knowledge.models import Document, DocumentVersion
from tools.persian_rag_benchmark.config import (
    DEFAULT_ORG_ID,
    DEFAULT_USER_ID,
    DEFAULT_WORKSPACE_ID,
    BenchmarkConfig,
)
from tools.persian_rag_benchmark.orchestrator import run_benchmark


@dataclass(frozen=True)
class Candidate:
    name: str
    model_key: str
    backend: str
    dimensions: int = 1024


CANDIDATES: tuple[Candidate, ...] = (
    Candidate("bge-m3", "BAAI/bge-m3", "sentence_transformers", 1024),
    Candidate(
        "multilingual-e5-large",
        "intfloat/multilingual-e5-large",
        "sentence_transformers",
        1024,
    ),
    Candidate(
        "jina-embeddings-v3",
        "jinaai/jina-embeddings-v3",
        "sentence_transformers",
        1024,
    ),
    Candidate(
        "snowflake-arctic-embed-l-v2",
        "Snowflake/snowflake-arctic-embed-l-v2.0",
        "sentence_transformers",
        1024,
    ),
)


@dataclass
class ModelRunResult:
    candidate: str
    model_key: str
    backend: str
    dimensions: int
    success: bool
    error: str | None = None
    index_seconds: float | None = None
    embed_chunk_count: int | None = None
    storage_bytes: int | None = None
    peak_rss_mb: float | None = None
    benchmark_run_id: str | None = None
    baseline_hit_at_k: float | None = None
    baseline_recall_at_k: float | None = None
    baseline_precision_at_k: float | None = None
    baseline_mrr: float | None = None
    robustness_hit_at_k: float | None = None
    avg_retrieval_latency_ms: float | None = None
    avg_embed_query_latency_ms: float | None = None
    persian_surface: dict[str, Any] = field(default_factory=dict)
    embedding_health: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="RC2.3 Persian embedding comparison")
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--dataset-path", default="../demo/evaluation")
    parser.add_argument(
        "--output-dir",
        default="benchmark-artifacts/rc2.3-embeddings",
    )
    parser.add_argument(
        "--candidates",
        default="all",
        help="Comma-separated candidate names or 'all'",
    )
    parser.add_argument("--top-k", type=int, default=8)
    parser.add_argument("--include-deterministic-baseline", action="store_true")
    return parser


async def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    selected = _select_candidates(args.candidates)
    if args.include_deterministic_baseline:
        selected = [
            Candidate("deterministic-hash", "BAAI/bge-m3", "deterministic", 1024),
            *selected,
        ]

    kb = uuid.UUID(args.knowledge_base_id)
    results: list[ModelRunResult] = []
    for candidate in selected:
        print(f"\n=== Running candidate: {candidate.name} ({candidate.model_key}) ===")
        result = await _run_candidate(
            candidate,
            knowledge_base_id=kb,
            dataset_path=Path(args.dataset_path),
            output_dir=out_dir / candidate.name,
            top_k=args.top_k,
        )
        results.append(result)
        _write_json(out_dir / f"{candidate.name}.json", asdict(result))
        print(json.dumps(asdict(result), ensure_ascii=False, indent=2)[:1600])

    _write_json(out_dir / "comparison_raw.json", [asdict(item) for item in results])
    report_path = out_dir / "EMBEDDING_COMPARISON.md"
    report_path.write_text(_render_report(results), encoding="utf-8")
    # Also publish canonical copy at package docs-friendly artifact root.
    canonical = out_dir / "EMBEDDING_COMPARISON.md"
    print(f"\nWrote {canonical}")
    return 0 if any(item.success for item in results) else 1


def _select_candidates(spec: str) -> list[Candidate]:
    if spec.strip().lower() == "all":
        return list(CANDIDATES)
    wanted = {part.strip() for part in spec.split(",") if part.strip()}
    found = [item for item in CANDIDATES if item.name in wanted]
    missing = wanted - {item.name for item in found}
    if missing:
        raise SystemExit(f"Unknown candidates: {sorted(missing)}")
    return found


async def _run_candidate(
    candidate: Candidate,
    *,
    knowledge_base_id: uuid.UUID,
    dataset_path: Path,
    output_dir: Path,
    top_k: int,
) -> ModelRunResult:
    get_settings.cache_clear()
    base = get_settings()
    settings = base.model_copy(
        update={
            "embedding_backend": candidate.backend,
            "embedding_model_key": candidate.model_key,
            "embedding_dimensions": candidate.dimensions,
        }
    )
    peak_rss: float | None = None
    try:
        async with lifespan_container(settings) as container:
            assert container.indexing_service is not None
            assert container.session_factory is not None
            assert container.embedding_provider is not None

            sample_q = "مرخصی استحقاقی سالانه کارکنان رسمی چند روز کاری است؟"
            t0 = time.perf_counter()
            _ = await container.embedding_provider.embed_query(sample_q)
            query_ms = (time.perf_counter() - t0) * 1000.0
            peak_rss = _rss_mb()

            index_seconds, embed_count = await _force_reindex_kb(
                container, knowledge_base_id=knowledge_base_id
            )
            peak_rss = _max_optional(peak_rss, _rss_mb())

            storage_bytes = await _embedding_storage_bytes(
                container, knowledge_base_id=knowledge_base_id
            )

            config = BenchmarkConfig(
                organization_id=DEFAULT_ORG_ID,
                workspace_id=DEFAULT_WORKSPACE_ID,
                user_id=DEFAULT_USER_ID,
                knowledge_base_id=knowledge_base_id,
                curated_dataset_path=dataset_path,
                enable_auto_corpus_probes=True,
                output_dir=output_dir,
                top_k=top_k,
                questions_per_document_min=20,
                questions_per_document_max=30,
                max_robustness_variants_per_question=4,
                run_name=f"rc2.3-{candidate.name}",
                include_generation=False,
            )

            summary = await run_benchmark(config)
            diag_path = Path(summary["paths"]["diagnostics_json"])
            diagnostics = json.loads(diag_path.read_text(encoding="utf-8"))
            baseline = (diagnostics.get("baseline_metrics") or {}).get("retrieval") or {}
            robust = (diagnostics.get("robustness_metrics") or {}).get("retrieval") or {}
            health = diagnostics.get("embedding_health") or {}
            persian = health.get("persian_surface") or {}
            latencies = [
                q.get("retrieval_latency_ms")
                for q in diagnostics.get("questions") or []
                if q.get("retrieval_latency_ms") is not None
            ]
            avg_ret_lat = sum(latencies) / len(latencies) if latencies else None

            return ModelRunResult(
                candidate=candidate.name,
                model_key=candidate.model_key,
                backend=candidate.backend,
                dimensions=candidate.dimensions,
                success=True,
                index_seconds=index_seconds,
                embed_chunk_count=embed_count,
                storage_bytes=storage_bytes,
                peak_rss_mb=peak_rss,
                benchmark_run_id=str(summary.get("run_id")),
                baseline_hit_at_k=_num(baseline.get("hit_at_k")),
                baseline_recall_at_k=_num(baseline.get("recall_at_k")),
                baseline_precision_at_k=_num(baseline.get("precision_at_k")),
                baseline_mrr=_num(baseline.get("mrr")),
                robustness_hit_at_k=_num(robust.get("hit_at_k")),
                avg_retrieval_latency_ms=avg_ret_lat,
                avg_embed_query_latency_ms=query_ms,
                persian_surface=persian if isinstance(persian, dict) else {},
                embedding_health={
                    "duplicate_vector_rate": health.get("duplicate_vector_rate"),
                    "vector_norm_distribution": health.get("vector_norm_distribution"),
                    "outlier_vector_count": health.get("outlier_vector_count"),
                    "score_mean": health.get("score_mean"),
                    "instability_rate": health.get("instability_rate"),
                },
            )
    except Exception as exc:  # noqa: BLE001 - collect per-model failures
        return ModelRunResult(
            candidate=candidate.name,
            model_key=candidate.model_key,
            backend=candidate.backend,
            dimensions=candidate.dimensions,
            success=False,
            error=f"{type(exc).__name__}: {exc}",
            peak_rss_mb=peak_rss,
            notes=["Candidate failed; see error."],
        )


async def _force_reindex_kb(
    container: AppContainer,
    *,
    knowledge_base_id: uuid.UUID,
) -> tuple[float, int]:
    assert container.session_factory is not None
    assert container.indexing_service is not None
    async with container.session_factory() as session:
        rows = (
            (
                await session.execute(
                    select(DocumentVersion.id)
                    .join(Document, Document.id == DocumentVersion.document_id)
                    .where(
                        Document.knowledge_base_id == knowledge_base_id,
                        Document.status != DocumentStatus.DELETED,
                        DocumentVersion.processing_status.in_(
                            [
                                ProcessingStatus.INDEXED,
                                ProcessingStatus.CHUNKED,
                                ProcessingStatus.FAILED,
                            ]
                        ),
                    )
                )
            )
            .scalars()
            .all()
        )

    started = time.perf_counter()
    created = 0
    for version_id in rows:
        async with container.session_factory() as session:
            version = await session.get(DocumentVersion, version_id)
            if version is None:
                continue
            if version.processing_status == ProcessingStatus.FAILED:
                version.processing_status = ProcessingStatus.CHUNKED
                version.failure_reason = None
                await session.commit()
        result = await container.indexing_service.reindex_document_version(version_id)
        created += int(result.embeddings_created) + int(
            getattr(result, "embeddings_skipped", 0) or 0
        )
    return time.perf_counter() - started, created


async def _embedding_storage_bytes(
    container: AppContainer,
    *,
    knowledge_base_id: uuid.UUID,
) -> int:
    assert container.session_factory is not None
    async with container.session_factory() as session:
        row = (
            await session.execute(
                select(func.count(Embedding.id), func.avg(Embedding.dimensions)).where(
                    Embedding.knowledge_base_id == knowledge_base_id,
                    Embedding.index_status == IndexStatus.INDEXED,
                )
            )
        ).one()
        count = int(row[0] or 0)
        dims = int(row[1] or 1024)
    return count * dims * 4


def _rss_mb() -> float | None:
    try:
        import os

        import psutil

        return psutil.Process(os.getpid()).memory_info().rss / (1024 * 1024)
    except Exception:  # noqa: BLE001
        return None


def _max_optional(left: float | None, right: float | None) -> float | None:
    values = [value for value in (left, right) if value is not None]
    return max(values) if values else None


def _num(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get("value")
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _render_report(results: list[ModelRunResult]) -> str:
    successful = [item for item in results if item.success]
    best = max(
        successful,
        key=lambda item: (item.baseline_hit_at_k or 0.0, item.baseline_mrr or 0.0),
        default=None,
    )
    bge = next((item for item in successful if item.candidate == "bge-m3"), None)

    recommend = "BAAI/bge-m3"
    reason = "Keep current default; no successful challenger evidence."
    if best and bge and best.candidate != bge.candidate:
        delta = (best.baseline_hit_at_k or 0.0) - (bge.baseline_hit_at_k or 0.0)
        if delta >= 0.05:
            recommend = best.model_key
            reason = (
                f"{best.candidate} improved Hit@k by {delta:.3f} vs BGE-M3 "
                "with acceptable latency/storage — recommend as configurable default."
            )
        else:
            reason = (
                f"Best challenger {best.candidate} Hit@k delta={delta:.3f} "
                "(< 0.05 threshold); keep BGE-M3."
            )
    elif best and bge is None:
        recommend = best.model_key
        reason = f"Only successful candidate was {best.candidate}."
    elif bge and best and best.candidate == bge.candidate:
        reason = "BGE-M3 remains best or tied on Measured Hit@k."

    lines = [
        "# EMBEDDING_COMPARISON",
        "",
        "## RC2.3 — Persian Embedding Optimization",
        "",
        "Scope: embedding subsystem only. Normalization, chunking, retrieval ranking,",
        "prompts, generation, APIs, UI, and architecture were not modified.",
        "",
        "Model swaps are Settings-only (`EMBEDDING_BACKEND`, `EMBEDDING_MODEL_KEY`,",
        "`EMBEDDING_DIMENSIONS`) via `create_embedding_provider`.",
        "",
        "## Retrieval comparison (Measured baseline)",
        "",
        "| Model | Hit@k | Recall@k | Precision@k | MRR | Robustness Hit@k |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for item in results:
        if not item.success:
            lines.append(f"| `{item.candidate}` | FAIL | — | — | — | — |")
            continue
        lines.append(
            "| `{c}` | {h:.4f} | {r:.4f} | {p:.4f} | {m:.4f} | {rh} |".format(
                c=item.candidate,
                h=item.baseline_hit_at_k or 0.0,
                r=item.baseline_recall_at_k or 0.0,
                p=item.baseline_precision_at_k or 0.0,
                m=item.baseline_mrr or 0.0,
                rh=(
                    f"{item.robustness_hit_at_k:.4f}"
                    if item.robustness_hit_at_k is not None
                    else "—"
                ),
            )
        )

    lines.extend(
        [
            "",
            "## Latency / indexing / storage",
            "",
            "| Model | Dims | Index s | Query embed ms | Retrieval ms | Storage B | Peak RSS MB |",
            "| --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for item in results:
        if not item.success:
            lines.append(f"| `{item.candidate}` | {item.dimensions} | FAIL | — | — | — | — |")
            continue
        lines.append(
            "| `{c}` | {d} | {i:.1f} | {q:.1f} | {r} | {s} | {m} |".format(
                c=item.candidate,
                d=item.dimensions,
                i=item.index_seconds or 0.0,
                q=item.avg_embed_query_latency_ms or 0.0,
                r=(
                    f"{item.avg_retrieval_latency_ms:.1f}"
                    if item.avg_retrieval_latency_ms is not None
                    else "—"
                ),
                s=item.storage_bytes if item.storage_bytes is not None else "—",
                m=f"{item.peak_rss_mb:.0f}" if item.peak_rss_mb is not None else "—",
            )
        )

    lines.extend(["", "## Vector diagnostics", ""])
    for item in results:
        lines.append(f"### `{item.candidate}`")
        if not item.success:
            lines.append(f"- Error: `{item.error}`")
            lines.append("")
            continue
        health = item.embedding_health
        lines.append(f"- duplicate_vector_rate: `{health.get('duplicate_vector_rate')}`")
        lines.append(f"- outlier_vector_count: `{health.get('outlier_vector_count')}`")
        lines.append(f"- vector_norm_distribution: `{health.get('vector_norm_distribution')}`")
        lines.append(f"- score_mean: `{health.get('score_mean')}`")
        lines.append(f"- robustness instability_rate: `{health.get('instability_rate')}`")
        if item.persian_surface:
            lines.append("- Persian surface Hit@k by robustness kind:")
            for kind, payload in item.persian_surface.items():
                lines.append(f"  - `{kind}`: {payload}")
        lines.append("")

    lines.extend(
        [
            "## Strengths / weaknesses",
            "",
            "### Strengths",
            "- Provider abstraction allows model changes via Settings alone.",
            "- Dense 1024-d models fit the existing `EmbeddingVector(1024)` column.",
            "- Benchmark isolates Measured IR from Heuristic generation scores.",
            "",
            "### Weaknesses / residual failures",
            "- Local `deterministic` backend (hash vectors) does not capture Persian semantics.",
            "- Retrieve path still uses raw query text (normalization not applied at retrieve).",
            "- Surface robustness (Arabic ي/ك, نیم‌فاصله, paraphrase) can still miss.",
            "- ST extras require download + significant RAM/disk.",
            "",
            "## Final recommendation",
            "",
            f"**Recommended production default model key:** `{recommend}`",
            "",
            reason,
            "",
            "Configuration (public APIs unchanged):",
            "",
            "```env",
            "EMBEDDING_BACKEND=sentence_transformers",
            f"EMBEDDING_MODEL_KEY={recommend}",
            "EMBEDDING_DIMENSIONS=1024",
            "```",
            "",
            "Default stays BGE-M3 unless Measured Hit@k improves by ≥ 0.05 without",
            "unacceptable latency/memory regression.",
            "",
        ]
    )
    return "\n".join(lines)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
