"""RC3.7 regression: golden E2E markers must match post-normalization chunk text."""

from __future__ import annotations

import json
from pathlib import Path

from rag_enterprise.processing.normalization import normalize_persian_text

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_GOLDEN = json.loads((_FIXTURES / "golden_path.json").read_text(encoding="utf-8"))
_DOCUMENT = (_FIXTURES / _GOLDEN["document_file"]).read_text(encoding="utf-8")


def test_golden_source_marker_matches_normalized_document_text() -> None:
    """Indexed retrieval returns normalized text; golden markers must use Latin digits."""
    normalized = normalize_persian_text(_DOCUMENT)
    marker = str(_GOLDEN["source_must_contain"])
    assert "۲۰" not in marker, "golden source marker must not use Persian digits"
    assert marker in normalized
    assert marker in str(_GOLDEN["expected_answer_fa"])


def test_persian_digits_in_source_document_normalize_to_latin() -> None:
    """Policy fixture still authors Persian digits; pipeline stores Latin equivalents."""
    assert "۲۰ روز کاری" in _DOCUMENT
    assert "20 روز کاری" in normalize_persian_text(_DOCUMENT)
    assert "۲۰ روز کاری" not in normalize_persian_text(_DOCUMENT)
