"""Citation validation and abstention parser tests."""

import uuid

from rag_enterprise.generation.citations import (
    extract_markers,
    is_model_abstention,
    is_substantive_answer,
    salvage_top_chunk_citation,
    strip_question_echo,
    validate_citations,
)
from rag_enterprise.generation.templates import v1
from rag_enterprise.retrieval.models import RetrievedChunk


def _chunk(text: str = "Employees receive 20 vacation days.") -> RetrievedChunk:
    chunk_id = uuid.uuid4()
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        score=0.8,
        text=text,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
    )


def test_extract_and_validate_citations() -> None:
    chunk = _chunk()
    markers = {"1": chunk.chunk_id}
    answer = "They get 20 days. [1]"
    assert extract_markers(answer) == ["1"]
    citations = validate_citations(answer=answer, markers=markers, chunks=[chunk])
    assert citations is not None
    assert len(citations) == 1
    assert citations[0].chunk_id == chunk.chunk_id
    assert citations[0].marker == "[1]"


def test_unknown_markers_fail_validation() -> None:
    chunk = _chunk()
    citations = validate_citations(
        answer="Invented claim [9]",
        markers={"1": chunk.chunk_id},
        chunks=[chunk],
    )
    assert citations is None


def test_model_abstention_detection_canonical() -> None:
    assert is_model_abstention("ABSTAIN: insufficient_evidence") == "insufficient_evidence"
    assert is_model_abstention("A normal answer [1]") is None


def test_model_abstention_detects_fragile_variants() -> None:
    cases = [
        ("ABSTAIN", "insufficient_evidence"),
        ("ABSTAIN:", "insufficient_evidence"),
        ("ABSTAIN: insufficient_evidence", "insufficient_evidence"),
        ("ABSTAIN: insufficient_evidence [1]", "insufficient_evidence"),
        ("ABSTAIN : insufficient_evidence", "insufficient_evidence"),
        ("ABSTAIN:\ninsufficient_evidence", "insufficient_evidence"),
        ("  abstain: insufficient_evidence  ", "insufficient_evidence"),
        (
            "ABSTAIN: insufficient_evidence[n]\n[n] chunk_id=019f… text: …",
            "insufficient_evidence",
        ),
        ("ABSTAIN: insufficient_evidence [3]", "insufficient_evidence"),
    ]
    for raw, expected in cases:
        assert is_model_abstention(raw) == expected, raw


def test_normal_answer_mentioning_abstain_word_is_not_abstention() -> None:
    answer = (
        "The policy says staff must not abstain from mandatory training. "
        "Attendance is required. [1]"
    )
    assert is_model_abstention(answer) is None


def test_strip_question_echo_persian() -> None:
    question = "درخواست انتقالی چگونه ثبت می‌شود؟"
    answer = f"{question}  فقط از طریق سامانه سجاد. [1]"
    cleaned = strip_question_echo(question, answer)
    assert "سجاد" in cleaned
    assert cleaned.startswith("درخواست") is False


def test_is_substantive_answer() -> None:
    assert is_substantive_answer("فقط از طریق سامانه سجاد انجام می‌شود. [1]") is True
    assert is_substantive_answer("[1]") is False
    assert is_substantive_answer("  ") is False


def test_salvage_top_chunk_citation() -> None:
    chunk = _chunk("مرخصی سالانه ۲۰ روز کاری است.")
    markers = {"1": chunk.chunk_id}
    citations = salvage_top_chunk_citation(chunks=[chunk], markers=markers)
    assert citations is not None
    assert citations[0].chunk_id == chunk.chunk_id
    assert citations[0].marker == "[1]"


def test_persian_abstain_message() -> None:
    assert "شواهد کافی" in v1.abstain_user_message("fa")
    assert "Insufficient evidence" in v1.abstain_user_message("en")
