"""Citation validation tests."""

import uuid

from rag_enterprise.generation.citations import (
    extract_markers,
    is_model_abstention,
    validate_citations,
)
from rag_enterprise.retrieval.models import RetrievedChunk


def _chunk() -> RetrievedChunk:
    chunk_id = uuid.uuid4()
    return RetrievedChunk(
        chunk_id=chunk_id,
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        score=0.8,
        text="Employees receive 20 vacation days.",
        chunk_index=0,
        start_char=0,
        end_char=34,
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


def test_model_abstention_detection() -> None:
    assert is_model_abstention("ABSTAIN: insufficient_evidence") == "insufficient_evidence"
    assert is_model_abstention("A normal answer [1]") is None
