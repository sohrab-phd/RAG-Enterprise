"""Context assembly unit tests."""

from __future__ import annotations

import uuid

from rag_enterprise.generation.context_assembly import assemble_context
from rag_enterprise.generation.prompt_builder import PromptBuilder
from rag_enterprise.retrieval.models import RetrievedChunk


def _chunk(
    *,
    text: str,
    score: float,
    chunk_index: int,
    heading: str | None = "مرخصی",
    document_id: uuid.UUID | None = None,
    document_version_id: uuid.UUID | None = None,
    chunk_id: uuid.UUID | None = None,
) -> RetrievedChunk:
    doc = document_id or uuid.uuid4()
    version = document_version_id or uuid.uuid4()
    return RetrievedChunk(
        chunk_id=chunk_id or uuid.uuid4(),
        document_id=doc,
        document_version_id=version,
        knowledge_base_id=uuid.uuid4(),
        score=score,
        text=text,
        chunk_index=chunk_index,
        start_char=0,
        end_char=len(text),
        heading=heading,
        language="fa",
    )


def test_dedupes_near_identical_chunks_keeps_higher_score() -> None:
    shared_doc = uuid.uuid4()
    shared_version = uuid.uuid4()
    high = _chunk(
        text="مرخصی استحقاقی سالانه ۲۰ روز است.",
        score=0.9,
        chunk_index=1,
        document_id=shared_doc,
        document_version_id=shared_version,
    )
    low = _chunk(
        text="مرخصی استحقاقی سالانه ۲۰ روز است.",
        score=0.5,
        chunk_index=9,
        document_id=shared_doc,
        document_version_id=shared_version,
    )
    result = assemble_context([high, low])
    assert result.duplicate_removal_count == 1
    assert result.duplicate_removed_ids == (low.chunk_id,)
    assert len(result.blocks) == 1
    assert result.blocks[0].primary.chunk_id == high.chunk_id


def test_merges_consecutive_same_heading_neighbors() -> None:
    doc = uuid.uuid4()
    version = uuid.uuid4()
    first = _chunk(
        text="بند اول سیاست.",
        score=0.8,
        chunk_index=10,
        document_id=doc,
        document_version_id=version,
    )
    second = _chunk(
        text="بند دوم استمرار.",
        score=0.7,
        chunk_index=11,
        document_id=doc,
        document_version_id=version,
    )
    unrelated = _chunk(
        text="سند دیگر.",
        score=0.95,
        chunk_index=0,
        heading="سایر",
    )
    result = assemble_context([unrelated, first, second])
    assert len(result.blocks) == 2
    merged = next(block for block in result.blocks if len(block.chunks) == 2)
    assert "بند اول سیاست." in merged.merged_text
    assert "بند دوم استمرار." in merged.merged_text
    assert merged.source_chunk_ids == (first.chunk_id, second.chunk_id)
    # Highest-score block first.
    assert result.blocks[0].primary.chunk_id == unrelated.chunk_id


def test_does_not_merge_non_consecutive_indexes() -> None:
    doc = uuid.uuid4()
    version = uuid.uuid4()
    first = _chunk(
        text="بخش الف",
        score=0.8,
        chunk_index=1,
        heading="الف",
        document_id=doc,
        document_version_id=version,
    )
    third = _chunk(
        text="بخش ج",
        score=0.7,
        chunk_index=3,
        heading="ج",
        document_id=doc,
        document_version_id=version,
    )
    result = assemble_context([first, third])
    assert len(result.blocks) == 2


def test_merges_consecutive_even_with_different_headings() -> None:
    doc = uuid.uuid4()
    version = uuid.uuid4()
    first = _chunk(
        text="بخش الف",
        score=0.8,
        chunk_index=1,
        heading="الف",
        document_id=doc,
        document_version_id=version,
    )
    second = _chunk(
        text="بخش ب",
        score=0.7,
        chunk_index=2,
        heading="ب",
        document_id=doc,
        document_version_id=version,
    )
    result = assemble_context([first, second])
    assert len(result.blocks) == 1
    assert "بخش الف" in result.blocks[0].merged_text
    assert "بخش ب" in result.blocks[0].merged_text


def test_overlap_join_avoids_duplicating_boundary() -> None:
    doc = uuid.uuid4()
    version = uuid.uuid4()
    first = _chunk(
        text="شروع متن مشترک پایان",
        score=0.8,
        chunk_index=1,
        document_id=doc,
        document_version_id=version,
    )
    second = _chunk(
        text="متن مشترک پایان ادامه",
        score=0.7,
        chunk_index=2,
        document_id=doc,
        document_version_id=version,
    )
    result = assemble_context([first, second])
    assert len(result.blocks) == 1
    assert result.blocks[0].merged_text == "شروع متن مشترک پایان ادامه"


def test_prompt_builder_preserves_secondary_citation_markers() -> None:
    doc = uuid.uuid4()
    version = uuid.uuid4()
    first = _chunk(
        text="اول",
        score=0.9,
        chunk_index=1,
        document_id=doc,
        document_version_id=version,
    )
    second = _chunk(
        text="دوم",
        score=0.6,
        chunk_index=2,
        document_id=doc,
        document_version_id=version,
    )
    built = PromptBuilder().build(
        question="سوال؟",
        chunks=[first, second],
        history=[],
        language_hint="fa",
    )
    assert "اول\nدوم" in built.user_prompt or "اولدوم" in built.user_prompt
    assert built.markers["1"] == first.chunk_id
    assert built.markers["2"] == second.chunk_id
    assert "[included in [1]]" in built.user_prompt
    assert "مرخصی" in built.user_prompt  # heading group label
    assert built.context_diagnostics["final_block_count"] == 1
    assert built.context_diagnostics["duplicate_removals"] == 0
