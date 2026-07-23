"""Run the fixed 20-question Golestan generation-quality evaluation."""

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

_BASE = "http://127.0.0.1:8300/api/v1"
_WORKSPACE_ID = "018f0000-0000-7000-8000-000000000002"
_HEADERS = {
    "X-Organization-Id": "018f0000-0000-7000-8000-000000000001",
    "X-User-Id": "018f0000-0000-7000-8000-000000000003",
    "Content-Type": "application/json",
}
_CITATION_RE = re.compile(r"\[(\d+)\]")
_PERSIAN_RE = re.compile(r"[\u0600-\u06FF]")
_LETTER_RE = re.compile(r"[^\W\d_]", re.UNICODE)
_NUMBERED_LIST_RE = re.compile(r"(?m)^\s*[۱-۹1-9][.)]\s+\S")
_ROBOTIC_PREFIXES = (
    "براساس اطلاعات موجود",
    "بر اساس اطلاعات موجود",
    "پرسش شما",
    "سؤال درباره",
    "سوال درباره",
)


@dataclass(frozen=True)
class EvaluationQuestion:
    question_id: str
    question: str
    facts: tuple[str, ...]
    expects_steps: bool = False


_QUESTIONS = (
    EvaluationQuestion(
        "q01",
        "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟",
        ("ادمین", "کیانی"),
    ),
    EvaluationQuestion(
        "q02",
        "آیا تغییر شناسه کاربری در گلستان توصیه می‌شود؟",
        ("خیر", "شماره دانشجویی", "رمز عبور"),
    ),
    EvaluationQuestion(
        "q03",
        "چگونه وارد سامانه گلستان شویم؟",
        ("دانشگاه من", "golestan.abru.ac.ir", "ورود به سیستم"),
        expects_steps=True,
    ),
    EvaluationQuestion("q04", "نام کاربری گلستان چیست؟", ("شماره دانشجویی",)),
    EvaluationQuestion("q05", "رمز عبور اولیه گلستان چیست؟", ("کد ملی",)),
    EvaluationQuestion(
        "q06",
        "اگر رمز عبور را فراموش کنیم چه باید کرد؟",
        ("کارشناس آموزش", "ریست", "تغییر رمز"),
        expects_steps=True,
    ),
    EvaluationQuestion(
        "q07",
        "انتخاب واحد از کدام بخش انجام می‌شود؟",
        ("ثبتنام", "ثبتنام اصلی"),
    ),
    EvaluationQuestion(
        "q08",
        "چرا اجازه انتخاب واحد ندارم؟",
        ("مشروط", "بدهی مالی", "پیشنیاز"),
    ),
    EvaluationQuestion(
        "q09",
        "پیش‌نیاز دروس یعنی چه؟",
        ("قبل", "ریاضی 1", "ریاضی 2"),
    ),
    EvaluationQuestion(
        "q10",
        "هم‌نیاز دروس یعنی چه؟",
        ("همزمان", "آزمایشگاه"),
    ),
    EvaluationQuestion(
        "q11",
        "حذف اضطراری چیست و آیا قابل برگشت است؟",
        ("قابل برگشت نیست",),
    ),
    EvaluationQuestion(
        "q12",
        "فرق حذف و اضافه با حذف اضطراری چیست؟",
        ("حذف و اضافه", "بدون نمره", "قابل برگشت"),
    ),
    EvaluationQuestion(
        "q13",
        "چگونه نمرات ترمی را مشاهده کنیم؟",
        ("اطلاعات جامع", "ترم"),
    ),
    EvaluationQuestion(
        "q14",
        "پرداخت شهریه از کدام بخش است؟",
        ("شهریه", "پرداختهای الکترونیکی"),
    ),
    EvaluationQuestion(
        "q15",
        "سقف مجاز انتخاب واحد چند واحد است؟",
        ("20", "24", "14"),
    ),
    EvaluationQuestion(
        "q16",
        "درخواست انتقالی چگونه ثبت می‌شود؟",
        ("سجاد", "نه مستقیما"),
    ),
    EvaluationQuestion(
        "q17",
        "در چه شرایطی معرفی به استاد داده می‌شود؟",
        ("دو درس",),
    ),
    EvaluationQuestion(
        "q18",
        "چگونه برنامه هفتگی را مشاهده کنیم؟",
        ("گزارش 88", "گزارش 78"),
    ),
    EvaluationQuestion(
        "q19",
        "اگر ارزشیابی اساتید را انجام ندهیم چه می‌شود؟",
        ("غیرفعال", "ارزشیابی"),
    ),
    EvaluationQuestion(
        "q20",
        "بهترین مرورگر برای گلستان چیست؟",
        ("Google Chrome", "Firefox"),
    ),
)


def main() -> int:
    """Run live generation and persist aggregate and per-question diagnostics."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--knowledge-base-id", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--base-url", default=_BASE)
    args = parser.parse_args()

    rows: list[dict[str, object]] = []
    with httpx.Client(timeout=240.0) as client:
        for item in _QUESTIONS:
            started = time.perf_counter()
            response = client.post(
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
            response.raise_for_status()
            payload = response.json()["data"]
            answer = str(payload.get("answer") or "")
            abstained = bool(payload.get("abstained"))
            facts_found = [fact for fact in item.facts if _normalize(fact) in _normalize(answer)]
            completeness = len(facts_found) / len(item.facts)
            verdict = (
                "fail"
                if abstained or completeness == 0
                else "pass"
                if completeness == 1
                else "partial"
            )
            citations = payload.get("citations") or []
            citation_markers = {
                str(citation.get("marker") or "")
                for citation in citations
                if isinstance(citation, dict)
            }
            answer_markers = {f"[{marker}]" for marker in _CITATION_RE.findall(answer)}
            paragraph_coverage = _paragraph_citation_coverage(answer)
            has_echo = _has_question_echo(item.question, answer)
            uses_robotic_prefix = _starts_with_robotic_prefix(answer)
            is_fluent_persian = _is_fluent_persian(
                answer,
                abstained=abstained,
                has_echo=has_echo,
            )
            rows.append(
                {
                    "id": item.question_id,
                    "question": item.question,
                    "expected_facts": list(item.facts),
                    "facts_found": facts_found,
                    "completeness": round(completeness, 4),
                    "verdict": verdict,
                    "abstained": abstained,
                    "answer": answer,
                    "citation_count": len(citations),
                    "citations_valid": bool(answer_markers)
                    and answer_markers.issubset(citation_markers),
                    "paragraph_citation_coverage": paragraph_coverage,
                    "question_echo": has_echo,
                    "robotic_prefix": uses_robotic_prefix,
                    "fluent_persian": is_fluent_persian,
                    "expects_steps": item.expects_steps,
                    "uses_numbered_steps": bool(_NUMBERED_LIST_RE.search(answer)),
                    "latency_ms": round(
                        (time.perf_counter() - started) * 1000,
                        2,
                    ),
                }
            )

    answered = [row for row in rows if not bool(row["abstained"])]
    step_rows = [row for row in rows if bool(row["expects_steps"])]
    summary = {
        "question_count": len(rows),
        "pass": sum(row["verdict"] == "pass" for row in rows),
        "partial": sum(row["verdict"] == "partial" for row in rows),
        "fail": sum(row["verdict"] == "fail" for row in rows),
        "abstains": sum(bool(row["abstained"]) for row in rows),
        "average_completeness": _mean(float(row["completeness"]) for row in rows),
        "citation_correctness": _mean(bool(row["citations_valid"]) for row in answered),
        "paragraph_citation_coverage": _mean(
            float(row["paragraph_citation_coverage"]) for row in answered
        ),
        "persian_fluency": _mean(bool(row["fluent_persian"]) for row in answered),
        "question_echoes": sum(bool(row["question_echo"]) for row in rows),
        "robotic_prefixes": sum(bool(row["robotic_prefix"]) for row in rows),
        "numbered_step_usage": _mean(bool(row["uses_numbered_steps"]) for row in step_rows),
        "average_latency_ms": round(
            _mean(float(row["latency_ms"]) for row in rows),
            2,
        ),
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(
            {"summary": summary, "results": rows},
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


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


def _paragraph_citation_coverage(answer: str) -> float:
    paragraphs = [
        paragraph.strip()
        for paragraph in re.split(
            r"\n\s*\n|(?=^\s*[۱-۹1-9][.)]\s+)",
            answer,
            flags=re.MULTILINE,
        )
        if len(_CITATION_RE.sub("", paragraph).strip()) >= 8
    ]
    if not paragraphs:
        return 0.0
    cited = sum(bool(_CITATION_RE.search(paragraph)) for paragraph in paragraphs)
    return round(cited / len(paragraphs), 4)


def _has_question_echo(question: str, answer: str) -> bool:
    normalized_question = _normalize(question)
    normalized_answer = _normalize(_CITATION_RE.sub("", answer))
    if normalized_question and normalized_answer.startswith(normalized_question):
        return True
    return _starts_with_robotic_prefix(answer, include_grounded_prefix=False)


def _starts_with_robotic_prefix(
    answer: str,
    *,
    include_grounded_prefix: bool = True,
) -> bool:
    prefixes = _ROBOTIC_PREFIXES if include_grounded_prefix else _ROBOTIC_PREFIXES[2:]
    normalized_answer = answer.strip().casefold()
    return any(normalized_answer.startswith(prefix.casefold()) for prefix in prefixes)


def _is_fluent_persian(
    answer: str,
    *,
    abstained: bool,
    has_echo: bool,
) -> bool:
    if abstained or has_echo or "\ufffd" in answer:
        return False
    letters = _LETTER_RE.findall(answer)
    if not letters:
        return False
    persian_letters = _PERSIAN_RE.findall(answer)
    return len(persian_letters) / len(letters) >= 0.55


def _mean(values: Iterable[float | int | bool]) -> float:
    collected = [float(value) for value in values]
    return round(sum(collected) / len(collected), 4) if collected else 0.0


if __name__ == "__main__":
    raise SystemExit(main())
