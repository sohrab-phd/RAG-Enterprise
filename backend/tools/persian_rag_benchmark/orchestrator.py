"""End-to-end orchestrator for the Persian RAG diagnostics benchmark."""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.persian_rag_benchmark.bootstrap import production_container
from tools.persian_rag_benchmark.config import BenchmarkConfig
from tools.persian_rag_benchmark.corpus import load_kb_chunks
from tools.persian_rag_benchmark.curated_gold import load_curated_dataset
from tools.persian_rag_benchmark.diagnostics.chunks import diagnose_chunks
from tools.persian_rag_benchmark.diagnostics.context_assembly import evaluate_context_assembly
from tools.persian_rag_benchmark.diagnostics.embeddings import diagnose_embeddings
from tools.persian_rag_benchmark.diagnostics.generation import evaluate_generation_by_cohort
from tools.persian_rag_benchmark.diagnostics.language import evaluate_language
from tools.persian_rag_benchmark.diagnostics.retrieval import evaluate_retrieval_by_cohort
from tools.persian_rag_benchmark.diagnostics.retrieval_detail import build_retrieval_detail
from tools.persian_rag_benchmark.diagnostics.root_cause import assign_root_causes
from tools.persian_rag_benchmark.ground_truth import generate_ground_truth
from tools.persian_rag_benchmark.models import GroundTruthQuestion, QuestionRunResult
from tools.persian_rag_benchmark.pipeline_runner import run_pipeline_for_questions
from tools.persian_rag_benchmark.reports import assemble_report, write_reports
from tools.persian_rag_benchmark.robustness import expand_robustness_variants


async def run_benchmark(config: BenchmarkConfig) -> dict[str, Any]:
    """Run the full Persian diagnostics workflow and write artifacts."""
    if config.knowledge_base_id is None:
        raise ValueError("knowledge_base_id is required")

    output_dir = config.resolve_output_dir()
    run_id = (
        f"{config.run_name}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"
    )
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    notes: list[str] = []

    async with production_container() as container:
        assert container.session_factory is not None
        chunks = await load_kb_chunks(
            container.session_factory,
            organization_id=config.organization_id,
            workspace_id=config.workspace_id,
            knowledge_base_id=config.knowledge_base_id,
            document_ids=config.document_ids,
        )
        if not chunks:
            raise RuntimeError(
                "No indexed chunks found for the knowledge base. "
                "Process & Index Persian documents before running the benchmark."
            )

        base_questions = _build_base_questions(config, chunks, notes)
        questions = expand_robustness_variants(
            base_questions,
            max_variants_per_question=config.max_robustness_variants_per_question,
            seed=config.seed,
        )
        _write_dataset(run_dir, questions, knowledge_base_id=str(config.knowledge_base_id))

        if config.dataset_only:
            return {
                "run_id": run_id,
                "output_dir": str(run_dir),
                "question_count": len(questions),
                "base_question_count": len(base_questions),
                "chunk_count": len(chunks),
                "dataset_only": True,
                "notes": notes,
            }

        results = await run_pipeline_for_questions(container, questions, config=config)
        results = assign_root_causes(results)

        retrieval_by_cohort = evaluate_retrieval_by_cohort(results, top_k=config.top_k)
        generation_by_cohort = (
            evaluate_generation_by_cohort(results)
            if config.include_generation
            else {
                "baseline": {"n": 0, "skipped": True},
                "robustness": {"n": 0, "skipped": True},
            }
        )
        language_health = evaluate_language(results)
        chunk_health = (
            diagnose_chunks(chunks, results)
            if config.include_chunk_diagnostics
            else {"chunk_count": len(chunks), "skipped": True}
        )
        embedding_health = (
            await diagnose_embeddings(
                results,
                settings=container.settings,
                embedding_provider=container.embedding_provider,
            )
            if config.include_embedding_diagnostics
            else {"skipped": True}
        )
        retrieval_detail = build_retrieval_detail(
            results,
            configured_top_k=config.top_k,
            configured_min_evidence_score=float(container.settings.generation_min_evidence_score),
        )
        context_assembly = evaluate_context_assembly(results)

        report = assemble_report(
            run_id=run_id,
            run_name=config.run_name,
            config={
                "organization_id": str(config.organization_id),
                "workspace_id": str(config.workspace_id),
                "knowledge_base_id": str(config.knowledge_base_id),
                "curated_dataset_path": (
                    str(config.curated_dataset_path) if config.curated_dataset_path else None
                ),
                "enable_auto_corpus_probes": config.enable_auto_corpus_probes,
                "top_k": config.top_k,
                "max_robustness_variants_per_question": (
                    config.max_robustness_variants_per_question
                ),
                "include_generation": config.include_generation,
                "seed": config.seed,
                "embedding_backend": container.settings.embedding_backend,
                "llm_backend": container.settings.llm_backend,
                "generation_min_evidence_score": float(
                    container.settings.generation_min_evidence_score
                ),
            },
            results=results,
            retrieval_by_cohort=retrieval_by_cohort,
            generation_by_cohort=generation_by_cohort,
            language_health=language_health,
            chunk_health=chunk_health,
            embedding_health=embedding_health,
            retrieval_detail=retrieval_detail,
            context_assembly=context_assembly,
            per_document=_per_document_stats(results),
            notes=notes,
        )
        paths = write_reports(report, run_dir)
        baseline_hit = (report.baseline_metrics.get("retrieval") or {}).get("hit_at_k")
        return {
            "run_id": run_id,
            "output_dir": str(run_dir),
            "paths": {key: str(path) for key, path in paths.items()},
            "baseline_hit_at_k": baseline_hit,
            "question_count": len(results),
            "base_question_count": len(base_questions),
            "chunk_count": len(chunks),
            "recommended_min_evidence_score": retrieval_detail.get(
                "recommended_min_evidence_score"
            ),
            "recommended_top_k": retrieval_detail.get("recommended_top_k"),
            "false_abstain_count": (retrieval_detail.get("false_abstains") or {}).get("count"),
            "avg_context_blocks": context_assembly.get("avg_final_blocks"),
            "avg_duplicate_removals": context_assembly.get("avg_duplicate_removals"),
            "notes": notes,
        }


def _build_base_questions(
    config: BenchmarkConfig,
    chunks: list[Any],
    notes: list[str],
) -> list[GroundTruthQuestion]:
    curated: list[GroundTruthQuestion] = []
    if config.curated_dataset_path is not None:
        curated = load_curated_dataset(
            config.curated_dataset_path,
            knowledge_base_id=str(config.knowledge_base_id),
            chunks=chunks,
        )
        notes.append(
            "Measured retrieval metrics use curated_external gold bound by passage text "
            f"from {config.curated_dataset_path}."
        )
    elif not config.enable_auto_corpus_probes:
        raise ValueError(
            "Provide --dataset-path with curated Feature-007 gold for Measured metrics, "
            "or pass --enable-auto-corpus-probes for non-Measured circular probes only."
        )

    probes: list[GroundTruthQuestion] = []
    if config.enable_auto_corpus_probes:
        probes = generate_ground_truth(
            chunks,
            knowledge_base_id=str(config.knowledge_base_id),
            questions_per_document_min=config.questions_per_document_min,
            questions_per_document_max=config.questions_per_document_max,
            seed=config.seed,
        )
        notes.append(
            "Auto corpus probes are included but eligible_for_measured_retrieval=false "
            "(circular gold excluded from Measured Hit@k/Recall@k/Precision@k/MRR)."
        )

    if not curated and not probes:
        raise ValueError("No questions produced.")

    if curated:
        return curated
    return probes


def _write_dataset(
    run_dir: Path,
    questions: list[GroundTruthQuestion],
    *,
    knowledge_base_id: str,
) -> None:
    dataset_dir = run_dir / "dataset"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = dataset_dir / "dataset.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as handle:
        for question in questions:
            handle.write(json.dumps(question.to_dataset_row(), ensure_ascii=False) + "\n")
    measured = sum(1 for q in questions if q.eligible_for_measured_retrieval)
    manifest = {
        "dataset_id": "persian-rag-benchmark",
        "dataset_version": "1.0.0",
        "knowledge_base_id": knowledge_base_id,
        "question_count": len(questions),
        "measured_eligible_count": measured,
        "languages": ["fa"],
        "language_default": "fa",
        "created_at": datetime.now(UTC).isoformat(),
        "notes": (
            "Baseline Measured metrics require curated_external gold. "
            "Auto corpus probes are never Measured for retrieval."
        ),
    }
    (dataset_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _per_document_stats(results: list[QuestionRunResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[QuestionRunResult]] = defaultdict(list)
    for item in results:
        if not item.eligible_for_measured_retrieval:
            continue
        grouped[item.expected_document_id or "unknown"].append(item)
    rows: list[dict[str, Any]] = []
    for document_id, items in sorted(grouped.items()):
        baseline = [item for item in items if item.cohort.value == "baseline"]
        robustness = [item for item in items if item.cohort.value == "robustness"]
        rows.append(
            {
                "document_id": document_id,
                "baseline_n": len(baseline),
                "baseline_hit_at_k": _mean_hit(baseline),
                "robustness_n": len(robustness),
                "robustness_hit_at_k": _mean_hit(robustness),
            }
        )
    return rows


def _mean_hit(items: list[QuestionRunResult]) -> float | None:
    values = [float(item.hit_at_k) for item in items if item.hit_at_k is not None]
    if not values:
        return None
    return sum(values) / len(values)
