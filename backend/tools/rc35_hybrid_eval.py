"""Run Golestan hybrid-retrieval diagnostics (dense + BM25 + RRF + RC3.2)."""

from __future__ import annotations

import argparse
import json
import re
import time
import unicodedata
from collections.abc import Iterable
from pathlib import Path

import httpx

_DEFAULT_BASE = "http://127.0.0.1:8800/api/v1"
_WORKSPACE_ID = "018f0000-0000-7000-8000-000000000002"
_HEADERS = {
    "X-Organization-Id": "018f0000-0000-7000-8000-000000000001",
    "X-User-Id": "018f0000-0000-7000-8000-000000000003",
    "Content-Type": "application/json",
}

_QUESTIONS = [
    ("q01", "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟", "کیانی"),
    ("q02", "آیا تغییر شناسه کاربری در گلستان توصیه می‌شود؟", "شماره دانشجویی"),
    ("q03", "چگونه وارد سامانه گلستان شویم؟", "golestan.abru.ac.ir"),
    ("q04", "نام کاربری گلستان چیست؟", "شماره دانشجویی"),
    ("q05", "رمز عبور اولیه گلستان چیست؟", "کد ملی"),
    ("q06", "اگر رمز عبور را فراموش کنیم چه باید کرد؟", "کارشناس آموزش"),
    ("q07", "انتخاب واحد از کدام بخش انجام می‌شود؟", "ثبتنام اصلی"),
    ("q08", "چرا اجازه انتخاب واحد ندارم؟", "بدهی مالی"),
    ("q09", "پیش‌نیاز دروس یعنی چه؟", "قبل از اخذ"),
    ("q10", "هم‌نیاز دروس یعنی چه؟", "همزمان"),
    ("q11", "حذف اضطراری چیست و آیا قابل برگشت است؟", "قابل برگشت نیست"),
    ("q12", "فرق حذف و اضافه با حذف اضطراری چیست؟", "بدون نمره"),
    ("q13", "چگونه نمرات ترمی را مشاهده کنیم؟", "اطلاعات جامع"),
    ("q14", "پرداخت شهریه از کدام بخش است؟", "پرداختهای الکترونیکی"),
    ("q15", "سقف مجاز انتخاب واحد چند واحد است؟", "20 واحد"),
    ("q16", "درخواست انتقالی چگونه ثبت می‌شود؟", "سجاد"),
    ("q17", "در چه شرایطی معرفی به استاد داده می‌شود؟", "دو درس"),
    ("q18", "چگونه برنامه هفتگی را مشاهده کنیم؟", "گزارش 88"),
    ("q19", "اگر ارزشیابی اساتید را انجام ندهیم چه می‌شود؟", "غیرفعال"),
    ("q20", "بهترین مرورگر برای گلستان چیست؟", "Google Chrome"),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default=_DEFAULT_BASE)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    with httpx.Client(timeout=240.0, trust_env=False) as client:
        for question_id, question, expected in _QUESTIONS:
            started = time.perf_counter()
            retrieval = client.post(
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/retrieve",
                headers=_HEADERS,
                json={
                    "query": question,
                    "knowledge_base_id": args.knowledge_base_id,
                    "top_k": 8,
                    "language": "fa",
                },
            )
            retrieval.raise_for_status()
            retrieval_ms = round((time.perf_counter() - started) * 1000, 2)
            chunks = retrieval.json()["data"]["results"]
            rank = _gold_rank(chunks, expected)
            wrong_faq = bool(chunks) and rank != 1

            chat_started = time.perf_counter()
            chat = client.post(
                f"{args.base_url}/workspaces/{_WORKSPACE_ID}/chat",
                headers=_HEADERS,
                json={
                    "question": question,
                    "knowledge_base_id": args.knowledge_base_id,
                    "conversation_id": None,
                    "top_k": 8,
                    "language_hint": "fa",
                },
            )
            chat.raise_for_status()
            data = chat.json()["data"]
            answer = data.get("answer") or ""
            abstained = bool(data.get("abstained"))
            answer_has_gold = _normalize(expected) in _normalize(answer)
            verdict = "abstain" if abstained else "pass" if answer_has_gold else "wrong"
            rows.append(
                {
                    "id": question_id,
                    "question": question,
                    "expected_marker": expected,
                    "gold_rank": rank,
                    "hit_at_1": rank == 1,
                    "hit_at_3": rank is not None and rank <= 3,
                    "hit_at_5": rank is not None and rank <= 5,
                    "reciprocal_rank": 0.0 if rank is None else 1.0 / rank,
                    "wrong_faq_retrieval": wrong_faq and rank is not None,
                    "top_chunks": [
                        {
                            "rank": index,
                            "score": chunk.get("score"),
                            "text": str(chunk.get("text") or "")[:220],
                        }
                        for index, chunk in enumerate(chunks[:5], start=1)
                    ],
                    "verdict": verdict,
                    "abstained": abstained,
                    "answer_has_gold": answer_has_gold,
                    "retrieval_latency_ms": retrieval_ms,
                    "latency_ms": round((time.perf_counter() - started) * 1000, 2),
                    "chat_latency_ms": round((time.perf_counter() - chat_started) * 1000, 2),
                }
            )

    summary = {
        "question_count": len(rows),
        "hit_at_1": _mean(bool(row["hit_at_1"]) for row in rows),
        "hit_at_3": _mean(bool(row["hit_at_3"]) for row in rows),
        "hit_at_5": _mean(bool(row["hit_at_5"]) for row in rows),
        "mrr": _mean(float(row["reciprocal_rank"]) for row in rows),
        "wrong_faq_retrieval": sum(bool(row["wrong_faq_retrieval"]) for row in rows),
        "pass": sum(row["verdict"] == "pass" for row in rows),
        "abstains": sum(row["verdict"] == "abstain" for row in rows),
        "wrong_answers": sum(row["verdict"] == "wrong" for row in rows),
        "false_abstains": sum(
            bool(row["abstained"]) and row["gold_rank"] is not None for row in rows
        ),
        "average_retrieval_latency_ms": round(
            _mean(float(row["retrieval_latency_ms"]) for row in rows),
            2,
        ),
        "average_latency_ms": round(_mean(float(row["latency_ms"]) for row in rows), 2),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps({"summary": summary, "results": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


def _gold_rank(chunks: list[dict[str, object]], expected: str) -> int | None:
    marker = _normalize(expected)
    for rank, chunk in enumerate(chunks, start=1):
        if marker in _normalize(str(chunk.get("text") or "")):
            return rank
    return None


def _normalize(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value)
    normalized = (
        normalized.replace("ي", "ی")
        .replace("ى", "ی")
        .replace("ك", "ک")
        .translate(
            str.maketrans(
                "۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩",
                "01234567890123456789",
            )
        )
    )
    return re.sub(r"[\W_]+", "", normalized).casefold()


def _mean(values: Iterable[float | int | bool]) -> float:
    collected = [float(value) for value in values]
    return round(sum(collected) / len(collected), 4) if collected else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
