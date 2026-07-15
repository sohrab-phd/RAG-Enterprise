"""Load curated external gold and bind it to live indexed chunks."""

from __future__ import annotations

import json
import re
from pathlib import Path

from tools.persian_rag_benchmark.models import (
    ChunkSnapshot,
    Difficulty,
    GroundTruthQuestion,
    QuestionCategory,
)
from tools.persian_rag_benchmark.trust import GoldProvenance


def load_curated_dataset(
    dataset_path: Path,
    *,
    knowledge_base_id: str,
    chunks: list[ChunkSnapshot],
) -> list[GroundTruthQuestion]:
    """Load Feature-007-style JSONL and bind citations to live chunks by passage text.

    Binding uses ``notes`` ``passage_contains=...`` or ``expected_answer`` / citation
    excerpts — never the originating auto-generated chunk id. This keeps gold
    independent of the retrieval index identity while allowing Measured Hit@k once
    bound to whatever live chunk currently holds that passage.
    """
    path = dataset_path
    if path.is_dir():
        path = path / "dataset.jsonl"
        if not path.exists():
            # demo package ships evaluation.jsonl
            alt = dataset_path / "evaluation.jsonl"
            path = alt if alt.exists() else path
    if not path.exists():
        raise FileNotFoundError(f"Curated dataset not found: {dataset_path}")

    questions: list[GroundTruthQuestion] = []
    with path.open(encoding="utf-8") as handle:
        for line_no, line in enumerate(handle, start=1):
            raw = line.strip()
            if not raw:
                continue
            row = json.loads(raw)
            bound = _bind_row(row, knowledge_base_id=knowledge_base_id, chunks=chunks)
            if bound is None:
                raise ValueError(
                    f"Unable to bind curated question {row.get('id', line_no)} "
                    "to any live chunk via passage text. Index the matching Persian "
                    "documents first, or fix passage_contains in notes."
                )
            questions.append(bound)
    if not questions:
        raise ValueError(f"Curated dataset is empty: {path}")
    return questions


def _bind_row(
    row: dict[str, object],
    *,
    knowledge_base_id: str,
    chunks: list[ChunkSnapshot],
) -> GroundTruthQuestion | None:
    question = str(row["question"])
    gold = str(row.get("expected_answer") or "")
    notes = str(row.get("notes") or "")
    needle = _passage_needle(notes, gold)
    match = _find_chunk(chunks, needle) if needle else None
    if match is None and gold:
        match = _find_chunk(chunks, gold[:80])
    if match is None and row.get("expect_abstention"):
        # Abstention cases intentionally have no corpus citation.
        return GroundTruthQuestion(
            id=str(row["id"]),
            question=question,
            gold_answer=gold,
            supporting_passage="",
            expected_citation_text="",
            expected_document_id="",
            expected_chunk_id="",
            knowledge_base_id=knowledge_base_id,
            category=_category_from_tags(row.get("tags")),
            difficulty=Difficulty(str(row.get("difficulty") or "easy")),
            keywords=[],
            tags=[str(tag) for tag in (row.get("tags") or ["fa"])],  # type: ignore[union-attr]
            language=str(row.get("language") or "fa"),
            expect_abstention=True,
            notes=notes or "curated_abstention",
            gold_provenance=GoldProvenance.CURATED_EXTERNAL,
            eligible_for_measured_retrieval=False,
        )
    if match is None:
        return None

    return GroundTruthQuestion(
        id=str(row["id"]),
        question=question,
        gold_answer=gold,
        supporting_passage=needle or match.text[:400],
        expected_citation_text=(needle or match.text)[:220],
        expected_document_id=str(match.document_id),
        expected_chunk_id=str(match.chunk_id),
        knowledge_base_id=knowledge_base_id,
        category=_category_from_tags(row.get("tags")),
        difficulty=Difficulty(str(row.get("difficulty") or "easy")),
        keywords=[],
        tags=[str(tag) for tag in (row.get("tags") or ["fa"])],  # type: ignore[union-attr]
        language=str(row.get("language") or "fa"),
        expect_abstention=bool(row.get("expect_abstention") or False),
        notes=notes or "curated_external_bound_by_passage",
        gold_provenance=GoldProvenance.CURATED_EXTERNAL,
        eligible_for_measured_retrieval=not bool(row.get("expect_abstention")),
    )


def _passage_needle(notes: str, gold: str) -> str:
    match = re.search(r"passage_contains=([^;]+)", notes)
    if match:
        return match.group(1).strip()
    return gold.strip()[:120]


def _find_chunk(chunks: list[ChunkSnapshot], needle: str) -> ChunkSnapshot | None:
    cleaned = re.sub(r"\s+", " ", needle).strip()
    if len(cleaned) < 4:
        return None
    for chunk in chunks:
        hay = re.sub(r"\s+", " ", chunk.text)
        if cleaned in hay:
            return chunk
    # Soft fallback: all tokens present
    tokens = [tok for tok in cleaned.split() if len(tok) > 1]
    if not tokens:
        return None
    for chunk in chunks:
        hay = chunk.text
        if all(tok in hay for tok in tokens[:6]):
            return chunk
    return None


def _category_from_tags(tags: object) -> QuestionCategory:
    values = [str(tag) for tag in (tags or [])] if isinstance(tags, list) else []
    mapping = {
        "leave": QuestionCategory.POLICY_LOOKUP,
        "remote": QuestionCategory.POLICY_LOOKUP,
        "travel": QuestionCategory.POLICY_LOOKUP,
        "handbook": QuestionCategory.FACTUAL,
        "abstain": QuestionCategory.FACTUAL,
    }
    for tag in values:
        if tag in mapping:
            return mapping[tag]
    return QuestionCategory.FACTUAL
