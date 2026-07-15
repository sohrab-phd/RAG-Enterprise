"""Unit tests for Persian RAG benchmark tool (no production mutation)."""

from __future__ import annotations

import uuid

from tools.persian_rag_benchmark.diagnostics.generation import score_answer
from tools.persian_rag_benchmark.diagnostics.root_cause import assign_root_causes
from tools.persian_rag_benchmark.ground_truth import generate_ground_truth
from tools.persian_rag_benchmark.models import (
    ChunkSnapshot,
    Difficulty,
    FailureLabel,
    GroundTruthQuestion,
    QuestionCategory,
    QuestionRunResult,
    RobustnessKind,
)
from tools.persian_rag_benchmark.persian_text import (
    arabic_yeh_kaf_variant,
    to_latin_digits,
    to_persian_digits,
)
from tools.persian_rag_benchmark.robustness import expand_robustness_variants


def _chunk(text: str, seq: int = 0) -> ChunkSnapshot:
    doc = uuid.UUID("018f0000-0000-7000-8000-00000000d001")
    ver = uuid.UUID("018f0000-0000-7000-8000-00000000e001")
    kb = uuid.UUID("018f0000-0000-7000-8000-0000000000b1")
    return ChunkSnapshot(
        chunk_id=uuid.uuid4(),
        document_id=doc,
        document_version_id=ver,
        knowledge_base_id=kb,
        sequence_number=seq,
        text=text,
        language="fa",
        document_title="سیاست مرخصی",
    )


def test_digit_normalization_helpers() -> None:
    assert to_latin_digits("۲۰ روز") == "20 روز"
    assert "۲۰" in to_persian_digits("20 روز")


def test_arabic_yeh_kaf_variant_changes_letters() -> None:
    source = "مرخصی کارکنان"
    variant = arabic_yeh_kaf_variant(source)
    assert variant != source


def test_ground_truth_generates_balanced_persian_questions() -> None:
    chunks = [
        _chunk(
            "مرخصی استحقاقی سالانه کارکنان رسمی ۲۰ روز کاری است. "
            "حداکثر پنج روز استفاده‌نشده با تأیید منابع انسانی منتقل می‌شود. "
            "مرخصی استعلاجی با گواهی پزشکی تا هفت روز پذیرفته می‌شود. "
            "دورکاری از سهمیه مرخصی کسر نمی‌شود و فقط با مجوز مدیر مجاز است.",
            seq=0,
        ),
        _chunk(
            "مهلت ثبت درخواست حداکثر سه روز کاری است. "
            "در صورت تعارض، سند تخصصی معیار است و واحد منابع انسانی مسئول پیگیری است.",
            seq=1,
        ),
    ]
    questions = generate_ground_truth(
        chunks,
        knowledge_base_id=str(chunks[0].knowledge_base_id),
        questions_per_document_min=40,
        questions_per_document_max=45,
        seed=7,
    )
    assert 40 <= len(questions) <= 45
    assert all(item.language == "fa" for item in questions)
    assert all(item.expected_chunk_id for item in questions)
    categories = {item.category for item in questions}
    assert QuestionCategory.FACTUAL in categories or QuestionCategory.NUMERICAL in categories


def test_robustness_expands_variants() -> None:
    base = GroundTruthQuestion(
        id="q1",
        question="مرخصی سالانه کارکنان چند روز است؟",
        gold_answer="۲۰ روز کاری",
        supporting_passage="مرخصی استحقاقی سالانه ۲۰ روز کاری است.",
        expected_citation_text="۲۰ روز کاری",
        expected_document_id="018f0000-0000-7000-8000-00000000d001",
        expected_chunk_id="018f0000-0000-7000-8000-00000000c001",
        knowledge_base_id="018f0000-0000-7000-8000-00000000kb01",
        category=QuestionCategory.NUMERICAL,
        difficulty=Difficulty.EASY,
        keywords=["مرخصی"],
        tags=["leave"],
    )
    expanded = expand_robustness_variants([base], max_variants_per_question=5, seed=1)
    assert len(expanded) == 1 + 5
    assert expanded[0].robustness_kind == RobustnessKind.NORMAL
    assert any(item.parent_question_id == "q1" for item in expanded[1:])


def test_score_answer_numeric_and_citation() -> None:
    scores = score_answer(
        gold="مرخصی سالانه ۲۰ روز کاری است.",
        predicted="بر اساس سند، مرخصی سالانه 20 روز کاری است.",
        expected_chunk_id="c1",
        cited_chunk_ids=["c1"],
        expected_citation_text="۲۰ روز کاری",
        category="numerical",
    )
    assert scores["citation_accuracy"] is True
    assert scores["numeric_accuracy"] == 1.0


def test_root_cause_labels_missed_retrieval() -> None:
    result = QuestionRunResult(
        question_id="q-fail",
        question="مرخصي سالانه چند روز است؟",
        normalized_question="مرخصی سالانه چند روز است؟",
        category="numerical",
        difficulty="easy",
        robustness_kind="arabic_yeh_kaf",
        gold_answer="۲۰",
        expected_chunk_id="c-expected",
        expected_document_id="d1",
        retrieved=[],
        retrieval_hit=False,
        correct_document=False,
        correct_chunk=False,
        language_issues=["arabic_yeh_or_kaf", "differs_from_production_normalize"],
        detected_language="fa",
    )
    labeled = assign_root_causes([result])[0]
    assert labeled.passed is False
    assert FailureLabel.RETRIEVAL in labeled.failure_labels
    assert labeled.failure_explanation
