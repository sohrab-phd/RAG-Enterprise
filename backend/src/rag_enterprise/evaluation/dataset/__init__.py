"""Golden dataset loader and validation."""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import ValidationError

from rag_enterprise.evaluation.exceptions import (
    DatasetNotFoundError,
    DatasetValidationError,
)
from rag_enterprise.evaluation.models import (
    DatasetManifest,
    DatasetQuestion,
    GoldenDataset,
)


def load_manifest(path: Path) -> DatasetManifest:
    """Load and validate ``manifest.json``."""
    if not path.is_file():
        raise DatasetNotFoundError(
            "dataset_not_found",
            details={"path": str(path), "artifact": "manifest.json"},
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetValidationError(
            "malformed dataset manifest",
            details={"path": str(path), "error": str(exc)},
        ) from exc
    try:
        return DatasetManifest.model_validate(payload)
    except ValidationError as exc:
        raise DatasetValidationError(
            "invalid dataset manifest",
            details={"path": str(path), "errors": exc.errors()},
        ) from exc


def load_questions(path: Path) -> list[DatasetQuestion]:
    """Load and validate JSONL question records."""
    if not path.is_file():
        raise DatasetNotFoundError(
            "dataset_not_found",
            details={"path": str(path), "artifact": "dataset.jsonl"},
        )
    questions: list[DatasetQuestion] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if not line:
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError as exc:
                raise DatasetValidationError(
                    "malformed dataset line",
                    details={"path": str(path), "line": line_number, "error": str(exc)},
                ) from exc
            try:
                questions.append(DatasetQuestion.model_validate(payload))
            except ValidationError as exc:
                raise DatasetValidationError(
                    "invalid dataset question",
                    details={
                        "path": str(path),
                        "line": line_number,
                        "errors": exc.errors(),
                    },
                ) from exc
    if not questions:
        raise DatasetValidationError(
            "dataset contains no questions",
            details={"path": str(path)},
        )
    _validate_question_ids(questions, path=path)
    return questions


def load_dataset(directory: Path | str) -> GoldenDataset:
    """Load a versioned golden dataset from a directory."""
    root = Path(directory)
    if not root.is_dir():
        raise DatasetNotFoundError(
            "dataset_not_found",
            details={"path": str(root)},
        )
    manifest = load_manifest(root / "manifest.json")
    questions = load_questions(root / "dataset.jsonl")
    if manifest.question_count is not None and manifest.question_count != len(questions):
        raise DatasetValidationError(
            "manifest question_count does not match dataset.jsonl",
            details={
                "expected": manifest.question_count,
                "actual": len(questions),
            },
        )
    kb_ids = {q.knowledge_base_id for q in questions}
    if len(kb_ids) > 1:
        raise DatasetValidationError(
            "dataset questions must share one knowledge_base_id in v1",
            details={"knowledge_base_ids": sorted(kb_ids)},
        )
    return GoldenDataset(manifest=manifest, questions=questions)


def _validate_question_ids(questions: list[DatasetQuestion], *, path: Path) -> None:
    seen: set[str] = set()
    for question in questions:
        if question.id in seen:
            raise DatasetValidationError(
                "duplicate question id",
                details={"path": str(path), "question_id": question.id},
            )
        seen.add(question.id)
        if question.expect_abstention:
            continue
        if not question.expected_citations and not question.expected_answer.strip():
            raise DatasetValidationError(
                "answerable question missing expected_answer and expected_citations",
                details={"path": str(path), "question_id": question.id},
            )
