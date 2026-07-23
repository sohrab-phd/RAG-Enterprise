"""Unit tests for RC3.6 deterministic evidence selection."""

from __future__ import annotations

import uuid

from rag_enterprise.generation.evidence_selection import (
    EvidenceLabel,
    select_evidence,
)
from rag_enterprise.retrieval.models import RetrievedChunk


def _chunk(
    *,
    text: str,
    score: float,
    heading: str | None = None,
    chunk_index: int = 0,
    document_id: uuid.UUID | None = None,
) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=document_id or uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        score=score,
        text=text,
        chunk_index=chunk_index,
        start_char=0,
        end_char=len(text),
        heading=heading,
        language="fa",
    )


def test_selects_primary_faq_over_distractor() -> None:
    gold = _chunk(
        text=("رمز عبور اولیه گلستان چیست؟\nرمز عبور اولیه معمولاً کد ملی دانشجو است."),
        score=0.78,
        heading="رمز عبور اولیه",
        chunk_index=1,
    )
    distractor = _chunk(
        text=(
            "اگر رمز عبور را فراموش کنیم چه باید کرد؟\n"
            "به کارشناس آموزش مراجعه کنید تا رمز را ریست کند."
        ),
        score=0.81,
        heading="فراموشی رمز",
        chunk_index=2,
    )
    filler = _chunk(
        text="سامانه گلستان برای امور آموزشی استفاده می‌شود.",
        score=0.55,
        heading="معرفی",
        chunk_index=0,
    )

    result = select_evidence(
        question="رمز عبور اولیه گلستان چیست؟",
        chunks=[distractor, gold, filler],
    )

    assert gold in result.primary
    assert distractor not in result.primary
    assert distractor in result.discarded or distractor in result.supplementary
    assert filler in result.discarded
    assert 1 <= len(result.primary) <= 3
    assert len(result.supplementary) <= 2
    assert all(chunk not in result.chunks_for_prompt for chunk in result.discarded)


def test_never_includes_irrelevant_in_prompt() -> None:
    relevant = _chunk(
        text="نام کاربری گلستان چیست؟\nنام کاربری همان شماره دانشجویی است.",
        score=0.9,
        heading="نام کاربری",
    )
    irrelevant = _chunk(
        text="بهترین مرورگر برای گلستان Google Chrome است.",
        score=0.7,
        heading="مرورگر",
    )
    result = select_evidence(
        question="نام کاربری گلستان چیست؟",
        chunks=[relevant, irrelevant],
    )
    assert relevant in result.chunks_for_prompt
    assert irrelevant not in result.chunks_for_prompt
    diagnostics = result.to_diagnostics()
    assert str(irrelevant.chunk_id) in diagnostics["discarded"]
    assert "selection_score" in diagnostics["candidates"][0]
    assert "selection_reason" in diagnostics["candidates"][0]


def test_limits_primary_and_supplementary_caps() -> None:
    doc = uuid.uuid4()
    chunks = [
        _chunk(
            text=f"سقف مجاز انتخاب واحد چند واحد است؟\nسقف عادی ۲۰ واحد است. بخش {index}.",
            score=0.9 - index * 0.01,
            heading="سقف واحد",
            chunk_index=index,
            document_id=doc,
        )
        for index in range(6)
    ]
    result = select_evidence(
        question="سقف مجاز انتخاب واحد چند واحد است؟",
        chunks=chunks,
    )
    assert len(result.primary) <= 3
    assert len(result.supplementary) <= 2
    assert len(result.chunks_for_prompt) <= 5
    assert len(result.discarded) >= 1


def test_conflict_when_primary_numbers_disagree() -> None:
    left = _chunk(
        text="سقف مجاز انتخاب واحد چند واحد است؟\nسقف مجاز ۲۰ واحد است.",
        score=0.88,
        heading="سقف",
        chunk_index=1,
    )
    right = _chunk(
        text="سقف مجاز انتخاب واحد چند واحد است؟\nسقف مجاز ۲۴ واحد برای معدل بالاست.",
        score=0.86,
        heading="سقف معدل",
        chunk_index=2,
    )
    result = select_evidence(
        question="سقف مجاز انتخاب واحد چند واحد است؟ ۲۰ یا ۲۴؟",
        chunks=[left, right],
    )
    assert len(result.primary) >= 2
    assert result.conflict is True
    assert result.conflict_reason is not None


def test_diagnostics_expose_required_fields() -> None:
    chunk = _chunk(
        text="چگونه وارد سامانه گلستان شویم؟\nبه آدرس golestan.abru.ac.ir بروید.",
        score=0.92,
        heading="ورود",
    )
    result = select_evidence(
        question="چگونه وارد سامانه گلستان شویم؟",
        chunks=[chunk],
    )
    diag = result.to_diagnostics()
    assert diag["selected_primary"]
    assert diag["selected_support"] == []
    assert diag["discarded"] == []
    assert diag["conflict"] is False
    candidate = diag["candidates"][0]
    assert candidate["label"] == EvidenceLabel.PRIMARY.value
    signals = candidate["signals"]
    for key in (
        "lexical_overlap",
        "persian_keyword_overlap",
        "heading_similarity",
        "faq_question_similarity",
        "exact_phrase",
        "numeric_agreement",
        "named_entities",
        "section_proximity",
        "rc32_ranking_score",
        "hybrid_rank_score",
    ):
        assert key in signals


def test_empty_input_returns_empty_selection() -> None:
    result = select_evidence(question="سوال بدون مدرک", chunks=[])
    assert result.chunks_for_prompt == []
    assert result.primary == ()
    assert result.discarded == ()
