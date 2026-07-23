"""Offline Golestan ranking before/after metrics for RC3.2 report."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from rag_enterprise.retrieval.models import RetrievedChunk
from rag_enterprise.retrieval.ranking import rank_dense_hits


def _chunk(text: str, score: float) -> RetrievedChunk:
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
        language="fa",
    )


CASES: list[dict[str, object]] = [
    {
        "id": "password_initial",
        "query": "رمز عبور اولیه گلستان چیست؟",
        "gold_text": "رمز عبور اولیه گلستان چیست؟\nبهصورت پیشفرض کد ملی دانشجو است.",
        "gold_cosine": 0.665,
        "distractors": [
            ("اگر رمز عبور را فراموش کنیم چه باید کرد؟\nتماس با کارشناس آموزش.", 0.735),
            ("مشکل فنی را به ادمین گزارش دهید.\nآقای کیانی", 0.65),
        ],
    },
    {
        "id": "password_short",
        "query": "رمز اولیه ورود چیست؟",
        "gold_text": "رمز عبور اولیه چیست؟\nکد ملی دانشجو.",
        "gold_cosine": 0.70,
        "distractors": [
            ("اگر رمز عبور را فراموش کنیم چه باید کرد؟\nتماس با کارشناس.", 0.72),
        ],
    },
    {
        "id": "username",
        "query": "نام کاربری گلستان چیست؟",
        "gold_text": "نام کاربری گلستان چیست؟\nشماره دانشجویی",
        "gold_cosine": 0.62,
        "distractors": [
            ("مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟\nادمین کیانی", 0.67),
        ],
    },
    {
        "id": "login",
        "query": "چگونه وارد سامانه گلستان شویم؟",
        "gold_text": "چگونه وارد سامانه گلستان شویم؟\nاز سایت دانشگاه بخش دانشگاه من وارد شوید.",
        "gold_cosine": 0.70,
        "distractors": [
            ("مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟\nادمین", 0.735),
        ],
    },
    {
        "id": "emergency_drop",
        "query": "حذف اضطراری چیست و آیا قابل برگشت است؟",
        "gold_text": "حذف اضطراری چیست؟\nپس از تایید نهایی قابل برگشت نیست.",
        "gold_cosine": 0.55,
        "distractors": [
            ("اگر پیشنیاز رعایت نشود چه میشود؟\nاجازه اخذ نمیدهد.", 0.589),
        ],
    },
    {
        "id": "transfer",
        "query": "درخواست انتقالی چگونه ثبت میشود؟",
        "gold_text": "درخواست انتقالی چگونه ثبت میشود؟\nفقط سامانه سجاد.",
        "gold_cosine": 0.52,
        "distractors": [
            ("دانشجوی مهمان چگونه انتخاب واحد میکند؟\nدر گلستان.", 0.54),
        ],
    },
    {
        "id": "unit_cap",
        "query": "سقف مجاز انتخاب واحد چند واحد است؟",
        "gold_text": "سقف مجاز انتخاب واحد چند واحد است؟\nکارشناسی 20 واحد.",
        "gold_cosine": 0.50,
        "distractors": [
            ("اگر واحد بیش از حد مجاز بگیریم چه میشود؟\nاجازه ثبت نمیدهد.", 0.593),
        ],
    },
    {
        "id": "browser",
        "query": "بهترین مرورگر برای گلستان چیست؟",
        "gold_text": "بهترین مرورگر برای گلستان چیست؟\nGoogle Chrome یا Firefox",
        "gold_cosine": 0.50,
        "distractors": [
            ("معدل کل از کجا قابل مشاهده است؟\nاطلاعات جامع.", 0.616),
        ],
    },
]


def main() -> None:
    before_hit = {1: 0, 3: 0, 5: 0}
    after_hit = {1: 0, 3: 0, 5: 0}
    before_mrr = 0.0
    after_mrr = 0.0
    examples: list[dict[str, object]] = []

    for case in CASES:
        gold = _chunk(str(case["gold_text"]), float(case["gold_cosine"]))  # type: ignore[arg-type]
        distractors = [
            _chunk(text, float(score))
            for text, score in case["distractors"]  # type: ignore[misc]
        ]
        pool = [gold, *distractors]
        cosine_order = sorted(pool, key=lambda item: (-item.score, str(item.chunk_id)))
        before_rank = next(
            index
            for index, item in enumerate(cosine_order, start=1)
            if item.chunk_id == gold.chunk_id
        )
        before_mrr += 1.0 / before_rank
        for k in (1, 3, 5):
            if before_rank <= k:
                before_hit[k] += 1

        ranked, diagnostics = rank_dense_hits(
            query=str(case["query"]),
            chunks=pool,
            top_k=5,
        )
        after_rank = next(
            index for index, item in enumerate(ranked, start=1) if item.chunk_id == gold.chunk_id
        )
        after_mrr += 1.0 / after_rank
        for k in (1, 3, 5):
            if after_rank <= k:
                after_hit[k] += 1

        examples.append(
            {
                "id": case["id"],
                "query": case["query"],
                "before_rank": before_rank,
                "after_rank": after_rank,
                "rank1": diagnostics.to_dict()["rankings"][0],
                "rank2": (
                    diagnostics.to_dict()["rankings"][1] if len(diagnostics.rankings) > 1 else None
                ),
            }
        )

    n = len(CASES)
    report = {
        "n": n,
        "before": {
            "hit_at_1": before_hit[1] / n,
            "hit_at_3": before_hit[3] / n,
            "hit_at_5": before_hit[5] / n,
            "mrr": before_mrr / n,
        },
        "after": {
            "hit_at_1": after_hit[1] / n,
            "hit_at_3": after_hit[3] / n,
            "hit_at_5": after_hit[5] / n,
            "mrr": after_mrr / n,
        },
        "examples": examples,
    }
    out = Path(__file__).resolve().parents[3] / "eval-artifacts" / "rc32-golestan-ranking.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    print(json.dumps(report["before"], indent=2))
    print(json.dumps(report["after"], indent=2))


if __name__ == "__main__":
    main()
