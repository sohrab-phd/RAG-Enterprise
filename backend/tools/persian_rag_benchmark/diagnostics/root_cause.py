"""Probabilistic root-cause analysis with confidence and evidence."""

from __future__ import annotations

from tools.persian_rag_benchmark.diagnostics.retrieval import explain_retrieval_miss
from tools.persian_rag_benchmark.models import QuestionRunResult, RcaFinding
from tools.persian_rag_benchmark.trust import EvaluationCohort, GoldProvenance


def assign_root_causes(results: list[QuestionRunResult]) -> list[QuestionRunResult]:
    updated: list[QuestionRunResult] = []
    for result in results:
        rca = _hypotheses(result)
        passed = _passed_measured(result)
        updated.append(result.model_copy(update={"rca": rca, "passed_measured": passed}))
    return updated


def _passed_measured(result: QuestionRunResult) -> bool:
    if not result.eligible_for_measured_retrieval:
        return False
    if not result.expected_chunk_id:
        # Curated abstention cases: measured success if model abstained.
        return result.abstained if result.generated_answer is not None or result.abstained else True
    if (result.hit_at_k or 0.0) < 1.0:
        return False
    if result.generated_answer is None:
        return True
    return not bool(result.hallucination_risk_estimate)


def _hypotheses(result: QuestionRunResult) -> list[RcaFinding]:
    findings: list[RcaFinding] = []

    if result.gold_provenance == GoldProvenance.AUTO_CORPUS_PROBE:
        findings.append(
            RcaFinding(
                likely_root_cause="AUTO_CORPUS_PROBE_NOT_MEASURED",
                confidence=1.0,
                evidence=[
                    "Gold provenance is auto_corpus_probe; retrieval Hit@k is circular "
                    "and excluded from Measured baseline metrics.",
                ],
            )
        )

    if result.eligible_for_measured_retrieval and (result.hit_at_k or 0.0) < 1.0:
        miss_evidence = explain_retrieval_miss(result)
        confidence = 0.55
        cause = "RETRIEVAL_MISS"
        if result.correct_document and not result.correct_chunk:
            cause = "LIKELY_WRONG_CHUNK_OR_CHUNKING"
            confidence = 0.65
        elif not result.correct_document and result.retrieved:
            cause = "LIKELY_WRONG_DOCUMENT_OR_EMBEDDING"
            confidence = 0.6
        if result.avg_retrieval_score is not None and result.avg_retrieval_score < 0.15:
            cause = "LIKELY_LOW_RETRIEVAL_SCORE"
            confidence = max(confidence, 0.7)
            miss_evidence.append(
                f"Average top-k retrieval score={result.avg_retrieval_score:.4f} < 0.15."
            )
        if result.cohort == EvaluationCohort.ROBUSTNESS:
            confidence = min(1.0, confidence + 0.1)
            miss_evidence.append(
                f"Failure observed on robustness variant kind={result.robustness_kind}."
            )
        findings.append(
            RcaFinding(
                likely_root_cause=cause,
                confidence=confidence,
                evidence=miss_evidence,
            )
        )

    if result.language_issues:
        issues = ", ".join(result.language_issues)
        findings.append(
            RcaFinding(
                likely_root_cause="LIKELY_QUERY_SURFACE_NORMALIZATION_GAP",
                confidence=0.45 if result.cohort == EvaluationCohort.ROBUSTNESS else 0.35,
                evidence=[
                    f"Surface issues on question text: {issues}.",
                    "Check whether query_text reached RetrievalService before "
                    "canonical normalize_persian_text (documents and queries share "
                    "the same pipeline before embed_query).",
                ],
            )
        )

    if result.generated_answer is not None and result.eligible_for_measured_retrieval:
        if result.citation_accuracy is False and result.expected_chunk_id:
            findings.append(
                RcaFinding(
                    likely_root_cause="LIKELY_CITATION_MISMATCH",
                    confidence=0.75,
                    evidence=[
                        f"Expected chunk {result.expected_chunk_id} not in citations "
                        f"{result.citations}.",
                    ],
                )
            )
        if result.hallucination_risk_estimate:
            findings.append(
                RcaFinding(
                    likely_root_cause="LIKELY_GENERATION_DRIFT",
                    confidence=0.4,
                    evidence=[
                        "Heuristic: lexical_overlap < 0.05 and citation miss.",
                        f"lexical_overlap={result.lexical_overlap}",
                    ],
                )
            )
        if result.abstained and result.gold_answer:
            max_score = max((hit.score for hit in result.retrieved), default=0.0)
            gold_hit = next(
                (hit for hit in result.retrieved if hit.chunk_id == result.expected_chunk_id),
                None,
            )
            false_abstain = (result.hit_at_k or 0.0) >= 1.0
            findings.append(
                RcaFinding(
                    likely_root_cause=(
                        "FALSE_ABSTAIN_EVIDENCE_THRESHOLD"
                        if false_abstain
                        else "LIKELY_ABSTENTION_POLICY"
                    ),
                    confidence=0.85 if false_abstain else 0.7,
                    evidence=[
                        f"generation_status={result.generation_status}",
                        "Gold answer expected but GenerationService abstained.",
                        f"max_retrieval_score={max_score:.4f}",
                        (
                            f"gold_chunk_score={gold_hit.score:.4f} rank={gold_hit.rank}"
                            if gold_hit is not None
                            else "gold chunk missing from top-k"
                        ),
                    ],
                )
            )

    findings.sort(key=lambda item: item.confidence, reverse=True)
    return findings[:5]
