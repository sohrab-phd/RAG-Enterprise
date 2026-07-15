"""Unit tests for Persian RAG benchmark RC1.7 trustworthiness fixes."""

from __future__ import annotations

import uuid

from tools.persian_rag_benchmark.diagnostics.generation import score_answer
from tools.persian_rag_benchmark.diagnostics.root_cause import assign_root_causes
from tools.persian_rag_benchmark.ground_truth import generate_ground_truth
from tools.persian_rag_benchmark.ir_metrics import (
    hit_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from tools.persian_rag_benchmark.models import (
    ChunkSnapshot,
    Difficulty,
    GroundTruthQuestion,
    QuestionCategory,
    QuestionRunResult,
    RcaFinding,
    RobustnessKind,
)
from tools.persian_rag_benchmark.persian_text import to_latin_digits
from tools.persian_rag_benchmark.robustness import expand_robustness_variants
from tools.persian_rag_benchmark.trust import (
    EvaluationCohort,
    GoldProvenance,
    MetricTrust,
)


def test_precision_at_k_uses_fixed_denominator_k() -> None:
    retrieved = ["a"]  # fewer than k
    expected = ["a"]
    # Standard P@5 = 1/5 when only one hit and k=5
    assert precision_at_k(retrieved, expected, k=5) == 0.2
    assert hit_at_k(retrieved, expected, k=5) == 1.0
    assert recall_at_k(retrieved, expected, k=5) == 1.0


def test_mrr_and_miss() -> None:
    assert reciprocal_rank(["x", "gold", "y"], ["gold"]) == 0.5
    assert reciprocal_rank(["x", "y"], ["gold"]) == 0.0


def test_auto_ground_truth_is_not_measured_eligible() -> None:
    chunk = ChunkSnapshot(
        chunk_id=uuid.uuid4(),
        document_id=uuid.UUID("018f0000-0000-7000-8000-0000000000d1"),
        document_version_id=uuid.UUID("018f0000-0000-7000-8000-0000000000e1"),
        knowledge_base_id=uuid.UUID("018f0000-0000-7000-8000-0000000000b1"),
        sequence_number=0,
        text=(
            "مرخصی استحقاقی سالانه کارکنان رسمی ۲۰ روز کاری است. "
            "حداکثر پنج روز استفاده‌نشده قابل انتقال است."
        ),
        language="fa",
    )
    questions = generate_ground_truth(
        [chunk],
        knowledge_base_id=str(chunk.knowledge_base_id),
        questions_per_document_min=40,
        questions_per_document_max=40,
        seed=1,
    )
    assert questions
    assert all(item.gold_provenance == GoldProvenance.AUTO_CORPUS_PROBE for item in questions)
    assert all(item.eligible_for_measured_retrieval is False for item in questions)


def test_robustness_preserves_provenance_and_is_separate_cohort() -> None:
    base = GroundTruthQuestion(
        id="q1",
        question="مرخصی سالانه کارکنان چند روز است؟",
        gold_answer="۲۰ روز کاری",
        supporting_passage="مرخصی استحقاقی سالانه ۲۰ روز کاری است.",
        expected_citation_text="۲۰ روز کاری",
        expected_document_id="018f0000-0000-7000-8000-0000000000d1",
        expected_chunk_id="018f0000-0000-7000-8000-0000000000c1",
        knowledge_base_id="018f0000-0000-7000-8000-0000000000b1",
        category=QuestionCategory.NUMERICAL,
        difficulty=Difficulty.EASY,
        keywords=["مرخصی"],
        tags=["leave"],
        gold_provenance=GoldProvenance.CURATED_EXTERNAL,
        eligible_for_measured_retrieval=True,
    )
    expanded = expand_robustness_variants([base], max_variants_per_question=3, seed=1)
    assert expanded[0].robustness_kind == RobustnessKind.NORMAL
    for variant in expanded[1:]:
        assert variant.parent_question_id == "q1"
        assert variant.gold_provenance == GoldProvenance.CURATED_EXTERNAL
        assert variant.eligible_for_measured_retrieval is True


def test_score_answer_renames_heuristics() -> None:
    scores = score_answer(
        gold="مرخصی سالانه ۲۰ روز کاری است.",
        predicted="بر اساس سند، مرخصی سالانه 20 روز کاری است.",
        expected_chunk_id="c1",
        cited_chunk_ids=["c1"],
        category="numerical",
    )
    assert "lexical_overlap" in scores
    assert "semantic_similarity" not in scores
    assert "heuristic_fluency_estimate" in scores
    assert scores["citation_accuracy"] is True
    assert scores["numeric_accuracy"] == 1.0
    assert to_latin_digits("۲۰") == "20"


def test_rca_returns_confidence_and_evidence() -> None:
    result = QuestionRunResult(
        question_id="q-fail",
        question="مرخصي سالانه چند روز است؟",
        normalized_question="مرخصی سالانه چند روز است؟",
        category="numerical",
        difficulty="easy",
        robustness_kind="arabic_yeh_kaf",
        cohort=EvaluationCohort.ROBUSTNESS,
        gold_provenance=GoldProvenance.CURATED_EXTERNAL,
        eligible_for_measured_retrieval=True,
        gold_answer="۲۰",
        expected_chunk_id="c-expected",
        expected_document_id="d1",
        retrieved=[],
        hit_at_k=0.0,
        recall_at_k=0.0,
        precision_at_k=0.0,
        mrr=0.0,
        language_issues=["arabic_yeh_or_kaf"],
        detected_language="fa",
    )
    labeled = assign_root_causes([result])[0]
    assert labeled.passed_measured is False
    assert labeled.rca
    assert isinstance(labeled.rca[0], RcaFinding)
    assert 0.0 <= labeled.rca[0].confidence <= 1.0
    assert labeled.rca[0].evidence


def test_metric_trust_enum_values() -> None:
    assert MetricTrust.MEASURED.value == "Measured"
    assert MetricTrust.HEURISTIC.value == "Heuristic"
