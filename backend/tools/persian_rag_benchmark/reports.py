"""HTML / JSON / CSV writers with Trust Report first."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from tools.persian_rag_benchmark.models import (
    BenchmarkReport,
    QuestionRunResult,
    SubsystemScore,
    TrustMetricRow,
)
from tools.persian_rag_benchmark.trust import (
    METRIC_DEFINITIONS,
    EvaluationCohort,
    MetricTrust,
)


def build_trust_report(
    *,
    baseline_retrieval: dict[str, Any],
    robustness_retrieval: dict[str, Any],
    baseline_generation: dict[str, Any],
    robustness_generation: dict[str, Any],
) -> list[TrustMetricRow]:
    rows: list[TrustMetricRow] = []
    for key, meta in METRIC_DEFINITIONS.items():
        trust = MetricTrust(meta["trust"])
        baseline_value: float | int | str | None = None
        robustness_value: float | int | str | None = None
        if key in {"hit_at_k", "recall_at_k", "precision_at_k", "mrr"}:
            baseline_value = baseline_retrieval.get(key)
            robustness_value = robustness_retrieval.get(key)
        elif key == "retrieval_score":
            baseline_value = baseline_retrieval.get("avg_retrieval_score")
            robustness_value = robustness_retrieval.get("avg_retrieval_score")
        elif key == "pass_rate":
            baseline_value = baseline_retrieval.get("measured_pass_rate")
            robustness_value = robustness_retrieval.get("measured_pass_rate")
        elif key in {
            "exact_match",
            "citation_accuracy",
            "numeric_accuracy",
            "lexical_overlap",
            "heuristic_fluency_estimate",
            "entity_match_estimate",
            "procedure_match_estimate",
            "groundedness_estimate",
        }:
            b = baseline_generation.get(_gen_key(key))
            r = robustness_generation.get(_gen_key(key))
            baseline_value = b.get("value") if isinstance(b, dict) else None
            robustness_value = r.get("value") if isinstance(r, dict) else None
        rows.append(
            TrustMetricRow(
                metric=key,
                trust=trust,
                definition=meta["definition"],
                baseline_value=baseline_value,
                robustness_value=robustness_value,
            )
        )
    return rows


def _gen_key(metric: str) -> str:
    mapping = {
        "exact_match": "exact_match_rate",
        "citation_accuracy": "citation_accuracy_rate",
        "numeric_accuracy": "numeric_accuracy_mean",
        "lexical_overlap": "lexical_overlap_mean",
        "heuristic_fluency_estimate": "heuristic_fluency_estimate_mean",
        "entity_match_estimate": "entity_match_estimate_mean",
        "procedure_match_estimate": "procedure_match_estimate_mean",
        "groundedness_estimate": "groundedness_estimate_rate",
    }
    return mapping.get(metric, metric)


def build_subsystem_scores(
    *,
    baseline_retrieval: dict[str, Any],
    robustness_retrieval: dict[str, Any],
    baseline_generation: dict[str, Any],
    robustness_generation: dict[str, Any],
) -> list[SubsystemScore]:
    scores: list[SubsystemScore] = []
    for cohort, retrieval, generation in (
        (EvaluationCohort.BASELINE, baseline_retrieval, baseline_generation),
        (EvaluationCohort.ROBUSTNESS, robustness_retrieval, robustness_generation),
    ):
        hit = retrieval.get("hit_at_k")
        scores.append(
            SubsystemScore(
                name="retrieval_hit_at_k",
                cohort=cohort,
                score=(float(hit) * 100.0) if hit is not None else None,
                trust=MetricTrust.MEASURED,
                computation="100 × mean Hit@k over eligible curated questions in this cohort",
                details={"n": retrieval.get("n"), "top_k": retrieval.get("top_k")},
            )
        )
        mrr = retrieval.get("mrr")
        scores.append(
            SubsystemScore(
                name="retrieval_mrr",
                cohort=cohort,
                score=(float(mrr) * 100.0) if mrr is not None else None,
                trust=MetricTrust.MEASURED,
                computation="100 × mean MRR over eligible curated questions in this cohort",
                details={"n": retrieval.get("n")},
            )
        )
        citation = generation.get("citation_accuracy_rate")
        citation_val = citation.get("value") if isinstance(citation, dict) else None
        scores.append(
            SubsystemScore(
                name="citation_accuracy",
                cohort=cohort,
                score=(float(citation_val) * 100.0) if citation_val is not None else None,
                trust=MetricTrust.MEASURED,
                computation=(
                    "100 × fraction of generated answers whose citations include expected_chunk_id"
                ),
                details={"n": generation.get("n")},
            )
        )
    return scores


def assemble_report(
    *,
    run_id: str,
    run_name: str,
    config: dict[str, Any],
    results: list[QuestionRunResult],
    retrieval_by_cohort: dict[str, Any],
    generation_by_cohort: dict[str, Any],
    language_health: dict[str, Any],
    chunk_health: dict[str, Any],
    embedding_health: dict[str, Any],
    per_document: list[dict[str, Any]],
    notes: list[str],
) -> BenchmarkReport:
    baseline_ret = dict(retrieval_by_cohort.get(EvaluationCohort.BASELINE.value) or {})
    robustness_ret = dict(retrieval_by_cohort.get(EvaluationCohort.ROBUSTNESS.value) or {})
    baseline_gen = dict(generation_by_cohort.get(EvaluationCohort.BASELINE.value) or {})
    robustness_gen = dict(generation_by_cohort.get(EvaluationCohort.ROBUSTNESS.value) or {})

    baseline_ret["measured_pass_rate"] = _pass_rate(
        [item for item in results if item.cohort == EvaluationCohort.BASELINE]
    )
    robustness_ret["measured_pass_rate"] = _pass_rate(
        [item for item in results if item.cohort == EvaluationCohort.ROBUSTNESS]
    )

    trust_report = build_trust_report(
        baseline_retrieval=baseline_ret,
        robustness_retrieval=robustness_ret,
        baseline_generation=baseline_gen,
        robustness_generation=robustness_gen,
    )
    subsystem_scores = build_subsystem_scores(
        baseline_retrieval=baseline_ret,
        robustness_retrieval=robustness_ret,
        baseline_generation=baseline_gen,
        robustness_generation=robustness_gen,
    )
    return BenchmarkReport(
        run_id=run_id,
        run_name=run_name,
        created_at=datetime.now(UTC).isoformat(),
        config=config,
        trust_report=trust_report,
        baseline_metrics={
            "retrieval": baseline_ret,
            "generation": baseline_gen,
        },
        robustness_metrics={
            "retrieval": robustness_ret,
            "generation": robustness_gen,
            "excluded_auto_corpus_probe_count": retrieval_by_cohort.get(
                "excluded_auto_corpus_probe_count"
            ),
        },
        subsystem_scores=subsystem_scores,
        persian_language_health=language_health,
        chunk_health=chunk_health,
        embedding_health=embedding_health,
        per_document=per_document,
        questions=results,
        notes=notes,
    )


def write_reports(report: BenchmarkReport, output_dir: Path) -> dict[str, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "diagnostics.json"
    csv_path = output_dir / "diagnostics.csv"
    html_path = output_dir / "diagnostics.html"
    trust_path = output_dir / "trust_report.json"

    payload = report.model_dump(mode="json")
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    trust_path.write_text(
        json.dumps(
            [row.model_dump(mode="json") for row in report.trust_report],
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    _write_csv(report.questions, csv_path)
    html_path.write_text(_render_html(report), encoding="utf-8")
    return {
        "diagnostics_json": json_path,
        "diagnostics_csv": csv_path,
        "diagnostics_html": html_path,
        "trust_report_json": trust_path,
    }


def _pass_rate(results: list[QuestionRunResult]) -> float | None:
    eligible = [item for item in results if item.eligible_for_measured_retrieval]
    if not eligible:
        return None
    return sum(1 for item in eligible if item.passed_measured) / len(eligible)


def _write_csv(results: list[QuestionRunResult], path: Path) -> None:
    fieldnames = [
        "question_id",
        "cohort",
        "gold_provenance",
        "eligible_for_measured_retrieval",
        "robustness_kind",
        "category",
        "question",
        "passed_measured",
        "hit_at_k",
        "recall_at_k",
        "precision_at_k",
        "mrr",
        "retrieval_rank",
        "avg_retrieval_score",
        "generated_answer",
        "gold_answer",
        "citations",
        "lexical_overlap_heuristic",
        "likely_root_cause",
        "rca_confidence",
        "e2e_latency_ms",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for item in results:
            top_rca = item.rca[0] if item.rca else None
            writer.writerow(
                {
                    "question_id": item.question_id,
                    "cohort": item.cohort.value,
                    "gold_provenance": item.gold_provenance.value,
                    "eligible_for_measured_retrieval": item.eligible_for_measured_retrieval,
                    "robustness_kind": item.robustness_kind,
                    "category": item.category,
                    "question": item.question,
                    "passed_measured": item.passed_measured,
                    "hit_at_k": item.hit_at_k,
                    "recall_at_k": item.recall_at_k,
                    "precision_at_k": item.precision_at_k,
                    "mrr": item.mrr,
                    "retrieval_rank": item.retrieval_rank,
                    "avg_retrieval_score": item.avg_retrieval_score,
                    "generated_answer": item.generated_answer,
                    "gold_answer": item.gold_answer,
                    "citations": "|".join(item.citations),
                    "lexical_overlap_heuristic": item.lexical_overlap,
                    "likely_root_cause": top_rca.likely_root_cause if top_rca else "",
                    "rca_confidence": top_rca.confidence if top_rca else "",
                    "e2e_latency_ms": item.e2e_latency_ms,
                }
            )


def _render_html(report: BenchmarkReport) -> str:
    trust_rows = []
    for row in report.trust_report:
        badge = row.trust.value
        trust_rows.append(
            "<tr>"
            f"<td>{_esc(row.metric)}</td>"
            f"<td><span class='badge {badge.lower()}'>{_esc(badge)}</span></td>"
            f"<td>{_fmt(row.baseline_value)}</td>"
            f"<td>{_fmt(row.robustness_value)}</td>"
            f"<td>{_esc(row.definition)}</td>"
            "</tr>"
        )

    subsystem_rows = []
    for item in report.subsystem_scores:
        subsystem_rows.append(
            "<tr>"
            f"<td>{_esc(item.name)}</td>"
            f"<td>{_esc(item.cohort.value)}</td>"
            f"<td>{_fmt(item.score)}</td>"
            f"<td><span class='badge {item.trust.value.lower()}'>"
            f"{_esc(item.trust.value)}</span></td>"
            f"<td>{_esc(item.computation)}</td>"
            "</tr>"
        )

    question_rows = []
    for item in report.questions[:200]:
        heuristic_bits = []
        if item.lexical_overlap is not None:
            heuristic_bits.append(f"Lexical Overlap (Heuristic)={item.lexical_overlap:.3f}")
        if item.heuristic_fluency_estimate is not None:
            heuristic_bits.append(
                f"Heuristic Fluency Estimate={item.heuristic_fluency_estimate:.3f}"
            )
        top_rca = item.rca[0] if item.rca else None
        rca_text = ""
        if top_rca:
            rca_text = (
                f"{top_rca.likely_root_cause} "
                f"(confidence={top_rca.confidence:.2f}); " + " | ".join(top_rca.evidence[:2])
            )
        question_rows.append(
            "<tr>"
            f"<td>{_esc(item.question_id)}</td>"
            f"<td>{_esc(item.cohort.value)}</td>"
            f"<td>{_esc(item.gold_provenance.value)}</td>"
            f"<td>{'Y' if item.passed_measured else 'N'}</td>"
            f"<td>{_fmt(item.hit_at_k)}</td>"
            f"<td>{_fmt(item.precision_at_k)}</td>"
            f"<td>{_fmt(item.mrr)}</td>"
            f"<td>{_esc(item.question)}</td>"
            f"<td>{_esc((item.generated_answer or '')[:160])}</td>"
            f"<td class='heuristic'>{_esc(' · '.join(heuristic_bits))}</td>"
            f"<td>{_esc(rca_text)}</td>"
            "</tr>"
        )

    notes = "".join(f"<li>{_esc(note)}</li>" for note in report.notes)
    metrics_blob = json.dumps(
        {
            "baseline": report.baseline_metrics,
            "robustness": report.robustness_metrics,
            "notes": report.notes,
        },
        ensure_ascii=False,
        indent=2,
    )
    health_blob = json.dumps(
        {
            "embedding": {
                "embedding_backend": report.embedding_health.get("embedding_backend"),
                "score_mean": report.embedding_health.get("score_mean"),
                "duplicate_vector_rate": report.embedding_health.get("duplicate_vector_rate"),
                "instability_rate": report.embedding_health.get("instability_rate"),
            },
            "language": report.persian_language_health,
            "chunks": {
                "chunk_count": report.chunk_health.get("chunk_count"),
                "never_retrieved_count": report.chunk_health.get("never_retrieved_count"),
            },
        },
        ensure_ascii=False,
        indent=2,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8"/>
  <title>Persian RAG Benchmark — {_esc(report.run_name)}</title>
  <style>
    body {{ font-family: Tahoma, "Segoe UI", sans-serif; margin: 2rem; color: #1f1a14;
      background: #f7f4ef; }}
    h1,h2,h3 {{ color: #0f3d2e; }}
    .badge {{ padding: 0.15rem 0.45rem; border-radius: 4px; font-size: 0.8rem; }}
    .measured {{ background: #d8efe0; }}
    .derived {{ background: #e7eef8; }}
    .estimated {{ background: #f7e8c8; }}
    .heuristic {{ background: #f3d6d0; }}
    table {{ width: 100%; border-collapse: collapse; background: white; margin-bottom: 1.5rem; }}
    th, td {{ border: 1px solid #ddd; padding: 0.4rem; vertical-align: top; font-size: 0.9rem; }}
    th {{ background: #e7efe9; }}
    td.heuristic {{ background: #fff4f2; }}
    .card {{ background: white; border: 1px solid #d9d2c5; border-radius: 8px;
      padding: 1rem; margin-bottom: 1rem; }}
    pre {{ background: white; border: 1px solid #ddd; padding: 0.75rem; overflow: auto; }}
  </style>
</head>
<body>
  <h1>Persian RAG Benchmark Diagnostics</h1>
  <p>Run <code>{_esc(report.run_id)}</code> · {_esc(report.created_at)}</p>

  <div class="card">
    <h2>1. Benchmark Trust Report (first page)</h2>
    <p>
      Every metric is labeled <strong>Measured</strong>, <strong>Derived</strong>,
      <strong>Estimated</strong>, or <strong>Heuristic</strong>.
      Baseline and Robustness columns are never mixed.
    </p>
    <table>
      <thead>
        <tr>
          <th>Metric</th><th>Trust</th><th>Baseline</th><th>Robustness</th>
          <th>How computed</th>
        </tr>
      </thead>
      <tbody>
        {"".join(trust_rows)}
      </tbody>
    </table>
  </div>

  <h2>2. Measured subsystem scores</h2>
  <p>No Version-1 Ready heuristic. Scores below are Measured (or empty if unavailable).</p>
  <table>
    <thead>
      <tr><th>Subsystem</th><th>Cohort</th><th>Score</th><th>Trust</th><th>Computation</th></tr>
    </thead>
    <tbody>
      {"".join(subsystem_rows)}
    </tbody>
  </table>

  <h2>3. Baseline vs Robustness metrics</h2>
  <pre>{_esc(metrics_blob)}</pre>

  <h2>4. Embedding / language / chunk health</h2>
  <pre>{_esc(health_blob)}</pre>

  <h2>5. Notes</h2>
  <ul>{notes}</ul>

  <h2>6. Per-question analysis (first 200)</h2>
  <p>
    Pink cells are <span class="badge heuristic">Heuristic</span> estimates only.
    Hit@k / Precision@k / MRR are <span class="badge measured">Measured</span>
    when gold provenance is curated_external.
  </p>
  <table>
    <thead>
      <tr>
        <th>ID</th><th>Cohort</th><th>Gold provenance</th><th>Passed (Measured)</th>
        <th>Hit@k</th><th>P@k</th><th>MRR</th><th>Question</th>
        <th>Generated</th><th>Heuristic estimates</th><th>Likely RCA</th>
      </tr>
    </thead>
    <tbody>
      {"".join(question_rows)}
    </tbody>
  </table>
</body>
</html>
"""


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    if isinstance(value, float):
        return f"{value:.4f}"
    return _esc(str(value))


def _esc(value: str) -> str:
    return (
        value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    )
