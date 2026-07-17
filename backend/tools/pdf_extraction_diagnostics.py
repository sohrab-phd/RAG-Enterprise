"""Compare persisted and current PDF extraction without storing document text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from typing import Any

import fitz

from rag_enterprise.processing.normalization import normalize_persian_text
from rag_enterprise.processing.service import DocumentProcessingService

_NUMBER_RE = re.compile(r"(?<!\w)\d+(?:[.,/-]\d+)*(?!\w)")
_ARABIC_VARIANT_RE = re.compile("[يك]")
_PUNCTUATION_SPACE_RE = re.compile(r"\s+[،؛؟!,:»)\]}]|[،؛؟!:](?=\S)")
_KNOWN_CORRUPT_INFORMATION = "اطالعات"
_CORRECT_INFORMATION = "اطلاعات"


def main() -> int:
    """Run diagnostics for explicit PDFs or local uploaded PDF files."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("pdf", nargs="*", type=Path)
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("../eval-artifacts/rc33-pdf-extraction.json"),
    )
    args = parser.parse_args()
    pdfs = args.pdf or sorted(Path("storage/uploads").rglob("*.pdf"))
    if not pdfs:
        parser.error("No PDF files found")

    result = {
        "schema_version": "1.0",
        "scope": "RC3.3 Persian PDF extraction",
        "documents": [_diagnose_pdf(path) for path in pdfs],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return 0


def _diagnose_pdf(path: Path) -> dict[str, object]:
    persisted_path = Path(f"{path}.extracted.txt")
    persisted = persisted_path.read_text(encoding="utf-8") if persisted_path.is_file() else ""
    native, modes, page_count = _inspect_modes(path)
    started = time.perf_counter()
    result = DocumentProcessingService().process_file(path)
    elapsed_ms = (time.perf_counter() - started) * 1000

    reference_numbers = _numbers(native)
    return {
        "document_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "page_count": page_count,
        "mode_diagnostics": modes,
        "persisted_baseline_available": bool(persisted),
        "before": _quality_metrics(persisted, reference_numbers),
        "after": _quality_metrics(result.text, reference_numbers),
        "elapsed_ms": round(elapsed_ms, 2),
        "warnings": result.warnings,
    }


def _inspect_modes(
    path: Path,
) -> tuple[str, list[dict[str, object]], int]:
    document = fitz.open(path)
    try:
        native_pages: list[str] = []
        mode_totals: dict[str, int] = {
            "text_default": 0,
            "text_sorted": 0,
            "blocks_sorted": 0,
            "words_sorted": 0,
            "dict": 0,
            "rawdict": 0,
        }
        for page in document:
            default_text = page.get_text("text")
            sorted_text = page.get_text("text", sort=True)
            raw = page.get_text("rawdict")
            native_pages.append(_raw_logical_text(raw))
            mode_totals["text_default"] += len(default_text)
            mode_totals["text_sorted"] += len(sorted_text)
            mode_totals["blocks_sorted"] += len(page.get_text("blocks", sort=True))
            mode_totals["words_sorted"] += len(page.get_text("words", sort=True))
            mode_totals["dict"] += len(page.get_text("dict").get("blocks", []))
            mode_totals["rawdict"] += len(raw.get("blocks", []))
        modes = [{"mode": mode, "units": value} for mode, value in mode_totals.items()]
        native = normalize_persian_text("\n\n".join(native_pages))
        return native, modes, document.page_count
    finally:
        document.close()


def _raw_logical_text(raw: dict[str, Any]) -> str:
    blocks = raw.get("blocks")
    if not isinstance(blocks, list):
        return ""
    values: list[str] = []
    for block in blocks:
        if not isinstance(block, dict) or block.get("type") != 0:
            continue
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                values.extend(char.get("c", "") for char in span.get("chars", []))
            values.append("\n")
        values.append("\n")
    return "".join(values)


def _quality_metrics(
    text: str,
    reference_numbers: list[str],
) -> dict[str, object]:
    numbers = _numbers(text)
    compared = min(len(numbers), len(reference_numbers))
    number_mismatches = sum(
        numbers[index] != reference_numbers[index] for index in range(compared)
    ) + abs(len(numbers) - len(reference_numbers))
    lines = text.splitlines()
    return {
        "characters": len(text),
        "lines": len(lines),
        "blank_lines": sum(not line.strip() for line in lines),
        "faq_questions": sum(line.rstrip().endswith(("؟", "?")) for line in lines),
        "number_tokens": len(numbers),
        "number_mismatches_vs_native_spans": number_mismatches,
        "replacement_characters": text.count("\ufffd"),
        "arabic_letter_variants": len(_ARABIC_VARIANT_RE.findall(text)),
        "known_glyph_order_artifacts": text.count(_KNOWN_CORRUPT_INFORMATION),
        "repaired_information_tokens": text.count(_CORRECT_INFORMATION),
        "punctuation_spacing_anomalies": len(_PUNCTUATION_SPACE_RE.findall(text)),
        "valid_golestan_url": "golestan.abru.ac.ir" in text,
    }


def _numbers(text: str) -> list[str]:
    return _NUMBER_RE.findall(text)


if __name__ == "__main__":
    raise SystemExit(main())
