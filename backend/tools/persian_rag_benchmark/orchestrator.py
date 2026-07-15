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
from tools.persian_rag_benchmark.diagnostics.chunks import diagnose_chunks
from tools.persian_rag_benchmark.diagnostics.embeddings import diagnose_embeddings
from tools.persian_rag_benchmark.diagnostics.generation import evaluate_generation
from tools.persian_rag_benchmark.diagnostics.language import evaluate_language
from tools.persian_rag_benchmark.diagnostics.retrieval import evaluate_retrieval
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

        base_questions = generate_ground_truth(
            chunks,
            knowledge_base_id=str(config.knowledge_base_id),
            questions_per_document_min=config.questions_per_document_min,
            questions_per_document_max=config.questions_per_document_max,
            seed=config.seed,
        )
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
            }

        results = await run_pipeline_for_questions(container, questions, config=config)
        results = assign_root_causes(results)

        retrieval_health = evaluate_retrieval(results, top_k=config.top_k)
        generation_health = (
            evaluate_generation(results) if config.include_generation else {"n": 0, "skipped": True}
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
        per_document = _per_document_stats(results)

        report = assemble_report(
            run_id=run_id,
            run_name=config.run_name,
            config={
                "organization_id": str(config.organization_id),
                "workspace_id": str(config.workspace_id),
                "knowledge_base_id": str(config.knowledge_base_id),
                "top_k": config.top_k,
                "questions_per_document_min": config.questions_per_document_min,
                "questions_per_document_max": config.questions_per_document_max,
                "max_robustness_variants_per_question": config.max_robustness_variants_per_question,
                "include_generation": config.include_generation,
                "seed": config.seed,
                "embedding_backend": container.settings.embedding_backend,
                "llm_backend": container.settings.llm_backend,
            },
            results=results,
            retrieval_health=retrieval_health,
            generation_health=generation_health,
            language_health=language_health,
            chunk_health=chunk_health,
            embedding_health=embedding_health,
            per_document=per_document,
        )
        paths = write_reports(report, run_dir)
        return {
            "run_id": run_id,
            "output_dir": str(run_dir),
            "paths": {key: str(path) for key, path in paths.items()},
            "overall_health_score": report.overall_health_score,
            "production_ready_for_persian": report.acceptance.production_ready_for_persian,
            "question_count": len(results),
            "base_question_count": len(base_questions),
            "chunk_count": len(chunks),
            "pass_rate": report.pipeline_health.get("pass_rate"),
        }


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
    manifest = {
        "dataset_id": "persian-rag-benchmark",
        "dataset_version": "1.0.0",
        "knowledge_base_id": knowledge_base_id,
        "question_count": len(questions),
        "languages": ["fa"],
        "language_default": "fa",
        "created_at": datetime.now(UTC).isoformat(),
        "notes": "Auto-generated by tools.persian_rag_benchmark for Version 1.0.0 diagnostics.",
    }
    (dataset_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _per_document_stats(results: list[QuestionRunResult]) -> list[dict[str, Any]]:
    grouped: dict[str, list[QuestionRunResult]] = defaultdict(list)
    for item in results:
        grouped[item.expected_document_id].append(item)
    rows: list[dict[str, Any]] = []
    for document_id, items in sorted(grouped.items()):
        rows.append(
            {
                "document_id": document_id,
                "n": len(items),
                "pass_rate": sum(1 for item in items if item.passed) / len(items),
                "retrieval_hit_rate": sum(1 for item in items if item.retrieval_hit) / len(items),
            }
        )
    return rows
