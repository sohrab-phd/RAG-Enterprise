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
