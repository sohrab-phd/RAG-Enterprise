"""PromptBuilder unit tests."""

import uuid

import pytest

from rag_enterprise.generation.exceptions import PromptTooLargeError
from rag_enterprise.generation.models import MessageRole, MessageTurn
from rag_enterprise.generation.prompt_builder import PromptBuilder, PromptBuilderConfig
from rag_enterprise.retrieval.models import RetrievedChunk


def _chunk(text: str, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        score=score,
        text=text,
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        heading="Policy",
        language="fa",
    )


def test_builds_versioned_prompt_with_history_and_markers() -> None:
    builder = PromptBuilder()
    chunks = [_chunk("مرخصی سالانه ۲۰ روز است.")]
    history = [
        MessageTurn(role=MessageRole.USER, content="سلام"),
        MessageTurn(role=MessageRole.ASSISTANT, content="سلام، بپرسید."),
    ]

    built = builder.build(
        question="سیاست مرخصی چیست؟",
        chunks=chunks,
        history=history,
        language_hint="fa",
    )

    assert built.template_version == "v1"
    assert "Persian" in built.system_prompt
    assert "Do NOT abstain when the answer is present" in built.system_prompt
    assert "HISTORY" in built.user_prompt
    assert "EVIDENCE" in built.user_prompt
    assert "[1]" in built.user_prompt
    assert "سیاست مرخصی چیست؟" in built.user_prompt
    assert "1" in built.markers
    assert built.markers["1"] == chunks[0].chunk_id


def test_clamps_history_window() -> None:
    builder = PromptBuilder(PromptBuilderConfig(max_history_messages=5))
    history = [MessageTurn(role=MessageRole.USER, content=f"q{i}") for i in range(12)]
    assert len(builder.clamp_history(history)) == 5


def test_prompt_too_large_raises() -> None:
    builder = PromptBuilder(PromptBuilderConfig(max_prompt_chars=80))
    huge = "x" * 500
    with pytest.raises(PromptTooLargeError):
        builder.build(question="q", chunks=[_chunk(huge)], history=[])


def test_detects_persian_language() -> None:
    builder = PromptBuilder()
    assert builder.detect_language("این یک سوال فارسی است") == "fa"
    assert builder.detect_language("What is the leave policy?") == "en"


def test_prompt_requires_complete_multi_chunk_synthesis_and_local_citations() -> None:
    builder = PromptBuilder()
    chunks = [
        _chunk("مرخصی استحقاقی کارکنان رسمی ۲۰ روز کاری در سال است.", 0.91),
        _chunk("حداکثر پنج روز مرخصی استفاده‌نشده به سال بعد منتقل می‌شود.", 0.88),
        _chunk("انتقال مرخصی نیازمند تأیید منابع انسانی است.", 0.86),
    ]

    built = builder.build(
        question="میزان مرخصی و شرایط انتقال آن چیست؟",
        chunks=chunks,
        history=[],
        language_hint="fa",
    )

    prompt = f"{built.system_prompt}\n{built.user_prompt}"
    assert "Inspect ALL EVIDENCE blocks" in prompt
    assert "Combine complementary facts from multiple blocks" in prompt
    assert "Cite every factual sentence" in prompt
    assert "If a sentence uses two blocks, cite both" in prompt
    assert "Never use one final" in prompt
    assert "[1]" in built.user_prompt
    assert "[2]" in built.user_prompt
    assert "[3]" in built.user_prompt


def test_prompt_specifies_conflicts_lists_tables_and_natural_persian() -> None:
    builder = PromptBuilder()
    built = builder.build(
        question="مراحل ثبت درخواست چیست؟",
        chunks=[_chunk("مرحله اول ثبت فرم و مرحله دوم تأیید مدیر است.")],
        history=[],
        language_hint="fa",
    )

    prompt = f"{built.system_prompt}\n{built.user_prompt}"
    assert "documents contain conflicting information" in prompt
    assert "Persian-numbered steps" in prompt
    assert "do not dump raw table rows" in prompt
    assert "پرسش شما" in prompt
    assert "براساس اطلاعات موجود" in prompt
    assert "Output only the final answer" in prompt


def test_prompt_preserves_exact_rc31_abstention_contract() -> None:
    built = PromptBuilder().build(
        question="پاسخ چیست؟",
        chunks=[_chunk("شواهد نامرتبط")],
        history=[],
        language_hint="fa",
    )

    assert "ABSTAIN: insufficient_evidence" in built.system_prompt
    assert "Do NOT abstain when the answer is present" in built.system_prompt
