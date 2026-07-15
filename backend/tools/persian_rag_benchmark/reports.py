"""HTML / JSON / CSV / acceptance report writers."""

from __future__ import annotations

import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from statistics import mean
from typing import Any

from tools.persian_rag_benchmark.models import (
    AcceptanceReport,
    BenchmarkReport,
    QuestionRunResult,
    SubsystemScore,
)


def build_acceptance_report(
    *,
    retrieval_health: dict[str, Any],
    generation_health: dict[str, Any],
    language_health: dict[str, Any],
    chunk_health: dict[str, Any],
    embedding_health: dict[str, Any],
    citation_health: dict[str, Any],
    results: list[QuestionRunResult],
) -> AcceptanceReport:
    subsystem = [
        SubsystemScore(
            name="retrieval",
            score=_pct(retrieval_health.get("hit_rate")),
            details=retrieval_health,
        ),
        SubsystemScore(
            name="generation",
            score=_pct(generation_health.get("groundedness_rate")),
            details=generation_health,
        ),
        SubsystemScore(
            name="citation",
            score=_pct(citation_health.get("citation_accuracy_rate")),
            details=citation_health,
        ),
        SubsystemScore(
            name="persian_language",
            score=max(0.0, 100.0 - 40.0 * float(language_health.get("normalize_delta_rate") or 0)),
            details=language_health,
        ),
        SubsystemScore(
            name="chunking",
            score=_chunk_score(chunk_health),
            details={"never_retrieved_count": chunk_health.get("never_retrieved_count")},
        ),
        SubsystemScore(
            name="embedding",
            score=max(
                0.0,
                100.0 - 80.0 * float(embedding_health.get("instability_rate") or 0),
            ),
            details=embedding_health,
        ),
    ]
    overall = mean(item.score for item in subsystem) if subsystem else 0.0
    failures = [item for item in results if not item.passed]
    cause_counter: Counter[str] = Counter()
    for item in failures:
        for label in item.failure_labels:
            cause_counter[label.value] += 1

    weaknesses: list[str] = []
    for score in sorted(subsystem, key=lambda item: item.score):
        if score.score < 70:
            weaknesses.append(f"{score.name} score is low ({score.score:.1f}/100)")

    recommendations = _recommendations(subsystem, cause_counter)
    ready = overall >= 75 and all(item.score >= 55 for item in subsystem)

    return AcceptanceReport(
        version="1.0.0",
        production_ready_for_persian=ready,
        overall_score=overall,
        subsystem_scores=subsystem,
        major_weaknesses=weaknesses[:8],
        top_failing_questions=[
            {
                "question_id": item.question_id,
                "question": item.question,
                "labels": [label.value for label in item.failure_labels],
                "explanation": item.failure_explanation,
            }
            for item in failures[:10]
        ],
        top_failure_causes=[
            {"label": label, "count": count} for label, count in cause_counter.most_common(10)
        ],
        recommendations=recommendations,
        notes=(
            "Acceptance is diagnostic guidance for Version 1.0.0 Persian RAG quality; "
            "it does not change product gates by itself."
        ),
    )


def assemble_report(
    *,
    run_id: str,
    run_name: str,
    config: dict[str, Any],
    results: list[QuestionRunResult],
    retrieval_health: dict[str, Any],
    generation_health: dict[str, Any],
    language_health: dict[str, Any],
    chunk_health: dict[str, Any],
    embedding_health: dict[str, Any],
    per_document: list[dict[str, Any]],
) -> BenchmarkReport:
    citation_health = {
        "citation_accuracy_rate": generation_health.get("citation_accuracy_rate"),
        "n": generation_health.get("n"),
    }
    acceptance = build_acceptance_report(
        retrieval_health=retrieval_health,
        generation_health=generation_health,
        language_health=language_health,
        chunk_health=chunk_health,
        embedding_health=embedding_health,
        citation_health=citation_health,
        results=results,
    )
    failure_categories = Counter(
        label.value for item in results if not item.passed for label in item.failure_labels
    )
    pipeline_health = {
        "pass_rate": mean(1.0 if item.passed else 0.0 for item in results) if results else 0.0,
        "n": len(results),
        "avg_e2e_latency_ms": mean(
            item.e2e_latency_ms for item in results if item.e2e_latency_ms is not None
        )
        if any(item.e2e_latency_ms is not None for item in results)
        else None,
    }
    return BenchmarkReport(
        run_id=run_id,
        run_name=run_name,
        created_at=datetime.now(UTC).isoformat(),
        config=config,
        overall_health_score=acceptance.overall_score,
        pipeline_health=pipeline_health,
        persian_language_health=language_health,
        retrieval_health=retrieval_health,
        generation_health=generation_health,
        citation_health=citation_health,
        chunk_health={
            "chunk_count": chunk_health.get("chunk_count"),
            "never_retrieved_count": chunk_health.get("never_retrieved_count"),
            "avg_chunk_chars": chunk_health.get("avg_chunk_chars"),
            "frequently_retrieved": chunk_health.get("frequently_retrieved"),
        },
        embedding_health=embedding_health,
        failure_categories=dict(failure_categories),
        per_document=per_document,
        questions=results,
        acceptance=acceptance,
        recommendations=acceptance.recommendations,
    )


def write_reports(report: BenchmarkReport, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "diagnostics.json"
    csv_path = output_dir / "diagnostics.csv"
    html_path = output_dir / "diagnostics.html"
    acceptance_path = output_dir / "acceptance_v1.json"

    json_path.write_text(
        json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    acceptance_path.write_text(
        json.dumps(report.acceptance.model_dump(mode="json"), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    _write_csv(report.questions, csv_path)
    html_path.write_text(_render_html(report), encoding="utf-8")
    return {
        "diagnostics_json": json_path,
        "diagnostics_csv": csv_path,
        "diagnostics_html": html_path,
        "acceptance_json": acceptance_path,
    }


def _write_csv(results: list[QuestionRunResult], path: Path) -> None:
    fieldnames = [
        "question_id",
        "robustness_kind",
        "category",
        "question",
        "passed",
        "retrieval_hit",
        "retrieval_rank",
        "avg_retrieval_score",
        "generated_answer",
        "gold_answer",
        "failure_labels",
        "failure_explanation",
        "e2e_latency_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            writer.writerow(
                {
                    "question_id": item.question_id,
                    "robustness_kind": item.robustness_kind,
                    "category": item.category,
                    "question": item.question,
                    "passed": item.passed,
                    "retrieval_hit": item.retrieval_hit,
                    "retrieval_rank": item.retrieval_rank,
                    "avg_retrieval_score": item.avg_retrieval_score,
                    "generated_answer": item.generated_answer,
                    "gold_answer": item.gold_answer,
                    "failure_labels": "|".join(label.value for label in item.failure_labels),
                    "failure_explanation": item.failure_explanation,
                    "e2e_latency_ms": item.e2e_latency_ms,
                }
            )


def _render_html(report: BenchmarkReport) -> str:
    rows = []
    for item in report.questions[:200]:
        status = "PASS" if item.passed else "FAIL"
        rows.append(
            "<tr>"
            f"<td>{_esc(item.question_id)}</td>"
            f"<td>{_esc(item.robustness_kind)}</td>"
            f"<td>{status}</td>"
            f"<td>{_esc(item.question)}</td>"
            f"<td>{_esc(item.gold_answer[:180])}</td>"
            f"<td>{_esc((item.generated_answer or '')[:180])}</td>"
            f"<td>{_esc(item.failure_explanation or '')}</td>"
            "</tr>"
        )
    subsystem_rows = "".join(
        f"<tr><td>{_esc(item.name)}</td><td>{item.score:.1f}</td></tr>"
        for item in report.acceptance.subsystem_scores
    )
    rec_items = "".join(
        f"<li><strong>{_esc(str(item.get('impact', '')))}</strong>: {_esc(str(item.get('action', '')))}</li>"
        for item in report.recommendations
    )
    ready = "YES" if report.acceptance.production_ready_for_persian else "NO"
    return f"""<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
  <meta charset="utf-8"/>
  <title>Persian RAG Diagnostics — {_esc(report.run_name)}</title>
  <style>
    body {{ font-family: Tahoma, "Segoe UI", sans-serif; margin: 2rem; background: #f7f4ef; color: #1f1a14; }}
    h1,h2 {{ color: #0f3d2e; }}
    .cards {{ display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 1rem; }}
    .card {{ background: white; border: 1px solid #d9d2c5; border-radius: 8px; padding: 1rem; }}
    table {{ width: 100%; border-collapse: collapse; background: white; }}
    th, td {{ border: 1px solid #ddd; padding: 0.45rem; vertical-align: top; font-size: 0.92rem; }}
    th {{ background: #e7efe9; }}
    .fail {{ color: #8b1e1e; }}
    .ok {{ color: #0f3d2e; }}
  </style>
</head>
<body>
  <h1>Persian RAG Diagnostics & Benchmark</h1>
  <p>Run <code>{_esc(report.run_id)}</code> · {_esc(report.created_at)}</p>
  <div class="cards">
    <div class="card"><strong>Overall Health</strong><div>{
        report.overall_health_score:.1f}/100</div></div>
    <div class="card"><strong>Version 1 Ready?</strong><div class="{
        "ok" if report.acceptance.production_ready_for_persian else "fail"
    }">{ready}</div></div>
    <div class="card"><strong>Pass Rate</strong><div>{
        float(report.pipeline_health.get("pass_rate") or 0):.1%}</div></div>
    <div class="card"><strong>Questions</strong><div>{report.pipeline_health.get("n")}</div></div>
  </div>

  <h2>Subsystem Scores</h2>
  <table><thead><tr><th>Subsystem</th><th>Score</th></tr></thead><tbody>{
        subsystem_rows
    }</tbody></table>

  <h2>Retrieval / Generation / Language</h2>
  <pre>{
        _esc(
            json.dumps(
                {
                    "retrieval": report.retrieval_health,
                    "generation": report.generation_health,
                    "language": report.persian_language_health,
                    "citation": report.citation_health,
                    "embedding": {
                        {
                            k: report.embedding_health.get(k)
                            for k in (
                                "embedding_backend",
                                "score_mean",
                                "instability_rate",
                                "duplicate_vector_rate",
                            )
                        }
                    },
                    "failures": report.failure_categories,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    }</pre>

  <h2>Recommendations (impact-ranked)</h2>
  <ol>{rec_items}</ol>

  <h2>Per-question analysis (first 200)</h2>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Variant</th><th>Status</th><th>Question</th>
        <th>Gold</th><th>Generated</th><th>Root cause</th>
      </tr>
    </thead>
    <tbody>
      {"".join(rows)}
    </tbody>
  </table>
</body>
</html>
"""


def _recommendations(
    subsystem: list[SubsystemScore],
    causes: Counter[str],
) -> list[dict[str, Any]]:
    recs: list[dict[str, Any]] = []
    by_name = {item.name: item.score for item in subsystem}
    if by_name.get("retrieval", 100) < 75:
        recs.append(
            {
                "impact": "high",
                "action": "Improve Persian PDF extraction and chunk boundaries; re-index corpus.",
            }
        )
    if by_name.get("embedding", 100) < 75 or causes.get("EMBEDDING", 0) > 0:
        recs.append(
            {
                "impact": "high",
                "action": (
                    "Evaluate a stronger Persian embedding backend (non-deterministic) "
                    "and add query-time Persian normalization before retrieve."
                ),
            }
        )
    if causes.get("TEXT_NORMALIZATION", 0) or causes.get("HALFSPACE_NORMALIZATION", 0):
        recs.append(
            {
                "impact": "high",
                "action": (
                    "Normalize Arabic ی/ک, digits, and ZWNJ on the query path "
                    "(currently production normalize runs at extract-time only)."
                ),
            }
        )
    if by_name.get("generation", 100) < 70:
        recs.append(
            {
                "impact": "medium",
                "action": "Use a real Persian-capable LLM backend instead of echo for generation QA.",
            }
        )
    if by_name.get("citation", 100) < 70:
        recs.append(
            {
                "impact": "medium",
                "action": "Tighten citation validation and evidence selection for Persian answers.",
            }
        )
    if by_name.get("chunking", 100) < 70:
        recs.append(
            {
                "impact": "medium",
                "action": "Tune chunk size/overlap for Persian policy sections and lists.",
            }
        )
    if not recs:
        recs.append(
            {
                "impact": "low",
                "action": "Maintain this benchmark as the official regression gate for every release.",
            }
        )
    return recs


def _pct(value: object) -> float:
    if value is None:
        return 0.0
    return float(value) * 100.0


def _chunk_score(chunk_health: dict[str, Any]) -> float:
    total = int(chunk_health.get("chunk_count") or 0)
    never = int(chunk_health.get("never_retrieved_count") or 0)
    if total <= 0:
        return 0.0
    return max(0.0, 100.0 * (1.0 - never / total))


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
