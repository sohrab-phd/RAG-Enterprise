"""RC3.6 Golestan evidence-selection benchmark (retrieve + select + chat)."""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

import httpx

from rag_enterprise.generation.evidence_selection import select_evidence
from rag_enterprise.retrieval.models import RetrievedChunk

_DEFAULT_BASE = "http://127.0.0.1:8800/api/v1"
_WORKSPACE_ID = "018f0000-0000-7000-8000-000000000002"
_HEADERS = {
    "X-Organization-Id": "018f0000-0000-7000-8000-000000000001",
    "X-User-Id": "018f0000-0000-7000-8000-000000000003",
    "Content-Type": "application/json",
}
_CITATION_RE = re.compile(r"\[(\d+)\]")


@dataclass(frozen=True)
class EvaluationQuestion:
    question_id: str
    question: str
    facts: tuple[str, ...]
    expected_marker: str


_QUESTIONS = (
    EvaluationQuestion(
        "q01",
        "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟",
        ("ادمین", "کیانی"),
        "کیانی",
    ),
    EvaluationQuestion(
        "q02",
        "آیا تغییر شناسه کاربری در گلستان توصیه می‌شود؟",
        ("خیر", "شماره دانشجویی", "رمز عبور"),
        "شماره دانشجویی",
    ),
    EvaluationQuestion(
        "q03",
        "چگونه وارد سامانه گلستان شویم؟",
        ("دانشگاه من", "golestan.abru.ac.ir", "ورود به سیستم"),
        "golestan.abru.ac.ir",
    ),
    EvaluationQuestion("q04", "نام کاربری گلستان چیست؟", ("شماره دانشجویی",), "شماره دانشجویی"),
    EvaluationQuestion("q05", "رمز عبور اولیه گلستان چیست؟", ("کد ملی",), "کد ملی"),
    EvaluationQuestion(
        "q06",
        "اگر رمز عبور را فراموش کنیم چه باید کرد؟",
        ("کارشناس آموزش", "ریست", "تغییر رمز"),
        "کارشناس آموزش",
    ),
    EvaluationQuestion(
        "q07",
        "انتخاب واحد از کدام بخش انجام می‌شود؟",
        ("ثبتنام", "ثبتنام اصلی"),
        "ثبتنام اصلی",
    ),
    EvaluationQuestion(
        "q08",
        "چرا اجازه انتخاب واحد ندارم؟",
        ("مشروط", "بدهی مالی", "پیشنیاز"),
        "بدهی مالی",
    ),
    EvaluationQuestion(
        "q09",
        "پیش‌نیاز دروس یعنی چه؟",
        ("قبل", "ریاضی 1", "ریاضی 2"),
        "قبل از اخذ",
    ),
    EvaluationQuestion(
        "q10",
        "هم‌نیاز دروس یعنی چه؟",
        ("همزمان", "آزمایشگاه"),
        "همزمان",
    ),
    EvaluationQuestion(
        "q11",
        "حذف اضطراری چیست و آیا قابل برگشت است؟",
        ("قابل برگشت نیست",),
        "قابل برگشت نیست",
    ),
    EvaluationQuestion(
        "q12",
        "فرق حذف و اضافه با حذف اضطراری چیست؟",
        ("حذف و اضافه", "بدون نمره", "قابل برگشت"),
        "بدون نمره",
    ),
    EvaluationQuestion(
        "q13",
        "چگونه نمرات ترمی را مشاهده کنیم؟",
        ("اطلاعات جامع", "ترم"),
        "اطلاعات جامع",
    ),
    EvaluationQuestion(
        "q14",
        "پرداخت شهریه از کدام بخش است؟",
        ("شهریه", "پرداختهای الکترونیکی"),
        "پرداختهای الکترونیکی",
    ),
    EvaluationQuestion(
        "q15",
        "سقف مجاز انتخاب واحد چند واحد است؟",
        ("20", "24", "14"),
        "20 واحد",
    ),
    EvaluationQuestion(
        "q16",
        "درخواست انتقالی چگونه ثبت می‌شود؟",
        ("سجاد", "نه مستقیما"),
        "سجاد",
    ),
    EvaluationQuestion(
        "q17",
        "در چه شرایطی معرفی به استاد داده می‌شود؟",
        ("دو درس",),
        "دو درس",
    ),
    EvaluationQuestion(
        "q18",
        "چگونه برنامه هفتگی را مشاهده کنیم؟",
        ("گزارش 88", "گزارش 78"),
        "گزارش 88",
    ),
    EvaluationQuestion(
        "q19",
        "اگر ارزشیابی اساتید را انجام ندهیم چه می‌شود؟",
        ("غیرفعال", "ارزشیابی"),
        "غیرفعال",
    ),
    EvaluationQuestion(
        "q20",
        "بهترین مرورگر برای گلستان چیست؟",
        ("Google Chrome", "Firefox"),
        "Google Chrome",
    ),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence-output", type=Path, required=True)
    parser.add_argument("--base-url", default=_DEFAULT_BASE)
    parser.add_argument("--skip-chat", action="store_true")
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    evidence_rows: list[dict[str, object]] = []

    with httpx.Client(timeout=240.0, trust_env=False) as client:
        for item in _QUESTIONS:
            started = time.perf_counter()
            retrieval = client.post(
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/retrieve",
                headers=_HEADERS,
                json={
                    "query": item.question,
                    "knowledge_base_id": args.knowledge_base_id,
                    "top_k": 8,
                    "language": "fa",
                },
            )
            retrieval.raise_for_status()
            retrieval_ms = round((time.perf_counter() - started) * 1000, 2)
            payload = retrieval.json()["data"]
            raw_chunks = payload["results"]
            chunks = [_to_chunk(row) for row in raw_chunks]
            gold_rank = _gold_rank(raw_chunks, item.expected_marker)

            selection = select_evidence(question=item.question, chunks=chunks)
            selection_diag = selection.to_diagnostics()
            selected_texts = [chunk.text for chunk in selection.chunks_for_prompt]
            gold_in_selected = any(
                _normalize(item.expected_marker) in _normalize(text) for text in selected_texts
            )
            original_chars = sum(len(str(row.get("text") or "")) for row in raw_chunks)
            selected_chars = sum(len(text or "") for text in selected_texts)
            prompt_reduction = (
                0.0 if original_chars == 0 else round(1.0 - (selected_chars / original_chars), 4)
            )

            evidence_rows.append(
                {
                    "id": item.question_id,
                    "question": item.question,
                    "expected_marker": item.expected_marker,
                    "gold_rank_retrieval": gold_rank,
                    "gold_in_selected": gold_in_selected,
                    "selected_primary": selection_diag["selected_primary"],
                    "selected_support": selection_diag["selected_support"],
                    "discarded": selection_diag["discarded"],
                    "conflict": selection_diag["conflict"],
                    "conflict_reason": selection_diag["conflict_reason"],
                    "selection_latency_ms": selection_diag["selection_latency_ms"],
                    "selected_chunk_count": len(selection.chunks_for_prompt),
                    "discarded_chunk_count": len(selection.discarded),
                    "original_char_estimate": original_chars,
                    "prompt_char_estimate": selected_chars,
                    "prompt_size_reduction": prompt_reduction,
                    "candidates": selection_diag["candidates"],
                }
            )

            verdict = "skip"
            abstained = False
            answer = ""
            facts_found: list[str] = []
            completeness = 0.0
            chat_ms = 0.0
            if not args.skip_chat:
                chat_started = time.perf_counter()
                chat = client.post(
                    f"{args.base_url}/workspaces/{_WORKSPACE_ID}/chat",
                    headers=_HEADERS,
                    json={
                        "question": item.question,
                        "knowledge_base_id": args.knowledge_base_id,
                        "conversation_id": None,
                        "top_k": 8,
                        "language_hint": "fa",
                    },
                )
                chat.raise_for_status()
                chat_ms = round((time.perf_counter() - chat_started) * 1000, 2)
                data = chat.json()["data"]
                answer = str(data.get("answer") or "")
                abstained = bool(data.get("abstained"))
                facts_found = [
                    fact for fact in item.facts if _normalize(fact) in _normalize(answer)
                ]
                completeness = len(facts_found) / len(item.facts)
                verdict = (
                    "fail"
                    if abstained or completeness == 0
                    else "pass"
                    if completeness == 1
                    else "partial"
                )

            rows.append(
                {
                    "id": item.question_id,
                    "question": item.question,
                    "expected_facts": list(item.facts),
                    "expected_marker": item.expected_marker,
                    "facts_found": facts_found,
                    "completeness": round(completeness, 4),
                    "verdict": verdict,
                    "abstained": abstained,
                    "answer": answer[:500],
                    "gold_rank": gold_rank,
                    "hit_at_1": gold_rank == 1,
                    "hit_at_3": gold_rank is not None and gold_rank <= 3,
                    "hit_at_5": gold_rank is not None and gold_rank <= 5,
                    "reciprocal_rank": 0.0 if gold_rank is None else 1.0 / gold_rank,
                    "gold_in_selected": gold_in_selected,
                    "selected_chunk_count": len(selection.chunks_for_prompt),
                    "discarded_chunk_count": len(selection.discarded),
                    "prompt_size_reduction": prompt_reduction,
                    "selection_latency_ms": selection.selection_latency_ms,
                    "retrieval_latency_ms": retrieval_ms,
                    "chat_latency_ms": chat_ms,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "citation_markers_in_answer": _CITATION_RE.findall(answer),
                }
            )

    summary = {
        "question_count": len(rows),
        "pass": sum(row["verdict"] == "pass" for row in rows),
        "partial": sum(row["verdict"] == "partial" for row in rows),
        "fail": sum(row["verdict"] == "fail" for row in rows),
        "hit_at_1": _mean(bool(row["hit_at_1"]) for row in rows),
        "hit_at_3": _mean(bool(row["hit_at_3"]) for row in rows),
        "mrr": _mean(float(row["reciprocal_rank"]) for row in rows),
        "gold_in_selected_rate": _mean(bool(row["gold_in_selected"]) for row in rows),
        "average_selected_chunks": round(
            _mean(float(row["selected_chunk_count"]) for row in rows),
            3,
        ),
        "average_discarded_chunks": round(
            _mean(float(row["discarded_chunk_count"]) for row in rows),
            3,
        ),
        "average_prompt_size_reduction": round(
            _mean(float(row["prompt_size_reduction"]) for row in rows),
            4,
        ),
        "average_selection_latency_ms": round(
            _mean(float(row["selection_latency_ms"]) for row in rows),
            3,
        ),
        "average_retrieval_latency_ms": round(
            _mean(float(row["retrieval_latency_ms"]) for row in rows),
            2,
        ),
        "average_chat_latency_ms": round(
            _mean(float(row["chat_latency_ms"]) for row in rows),
            2,
        ),
        "average_latency_ms": round(_mean(float(row["latency_ms"]) for row in rows), 2),
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"summary": summary, "results": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    args.evidence_output.parent.mkdir(parents=True, exist_ok=True)
    args.evidence_output.write_text(
        json.dumps(
            {
                "summary": {
                    "question_count": len(evidence_rows),
                    "gold_in_selected_rate": summary["gold_in_selected_rate"],
                    "average_selected_chunks": summary["average_selected_chunks"],
                    "average_discarded_chunks": summary["average_discarded_chunks"],
                    "average_prompt_size_reduction": summary["average_prompt_size_reduction"],
                    "average_selection_latency_ms": summary["average_selection_latency_ms"],
                },
                "results": evidence_rows,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _to_chunk(row: dict[str, object]) -> RetrievedChunk:
    import uuid

    return RetrievedChunk(
        chunk_id=uuid.UUID(str(row["chunk_id"])),
        document_id=uuid.UUID(str(row["document_id"])),
        document_version_id=uuid.UUID(str(row["document_version_id"])),
        knowledge_base_id=uuid.UUID(str(row["knowledge_base_id"])),
        score=float(row.get("score") or 0.0),
        text=str(row.get("text") or ""),
        chunk_index=int(row.get("chunk_index") or 0),
        start_char=int(row.get("start_char") or 0),
        end_char=int(row.get("end_char") or 0),
        heading=str(row["heading"]) if row.get("heading") is not None else None,
        language=str(row["language"]) if row.get("language") is not None else None,
    )


def _gold_rank(chunks: list[dict[str, object]], expected: str) -> int | None:
    marker = _normalize(expected)
    for rank, chunk in enumerate(chunks, start=1):
        if marker in _normalize(str(chunk.get("text") or "")):
            return rank
        if marker in _normalize(str(chunk.get("heading") or "")):
            return rank
    return None


def _normalize(value: str) -> str:
    text = unicodedata.normalize("NFKC", value).casefold()
    text = text.replace("\u200c", "").replace("ي", "ی").replace("ك", "ک")
    return re.sub(r"\s+", "", text)


def _mean(values: Iterable[bool | float]) -> float:
    items = list(values)
    if not items:
        return 0.0
    return float(sum(float(item) for item in items) / len(items))


if __name__ == "__main__":
    raise SystemExit(main())
