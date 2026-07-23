"""Unit tests for Persian FAQ dense ranking calibration (RC3.2)."""

from __future__ import annotations

import time
import uuid

from rag_enterprise.retrieval.models import RetrievedChunk
from rag_enterprise.retrieval.ranking import candidate_pool_size, rank_dense_hits


def _chunk(text: str, score: float, *, heading: str | None = None) -> RetrievedChunk:
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
        heading=heading,
        language="fa",
    )


def test_candidate_pool_expands_then_caps() -> None:
    assert candidate_pool_size(5) >= 10
    assert candidate_pool_size(40, max_top_k=50) == 50


def test_faq_question_overlap_promotes_correct_neighbor() -> None:
    """Classic Golestan miss: forget-password FAQ ranked above initial-password FAQ."""
    wrong = _chunk(
        "اگر رمز عبور را فراموش کنیم چه باید کرد؟\n"
        "دانشجو باید با کارشناس آموزش دانشکده تماس بگیرد.",
        score=0.735,
    )
    correct = _chunk(
        "رمز عبور اولیه گلستان چیست؟\nبهصورت پیشفرض کد ملی دانشجو است.",
        score=0.665,
    )
    query = "رمز عبور اولیه گلستان چیست؟"
    ranked, diagnostics = rank_dense_hits(query=query, chunks=[wrong, correct], top_k=2)

    assert ranked[0].chunk_id == correct.chunk_id
    assert ranked[0].score >= ranked[1].score
    assert diagnostics.rankings[0].cosine_score == 0.665
    assert diagnostics.rankings[0].adjusted_score > diagnostics.rankings[0].cosine_score
    assert "faq_question_overlap" in diagnostics.rankings[0].bonuses
    assert diagnostics.rankings[0].reasons_won


def test_username_faq_beats_admin_contact_chunk() -> None:
    admin = _chunk(
        "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟\n"
        "به ادمین سامانه گلستان دانشگاه (آقای کیانی)",
        score=0.67,
    )
    username = _chunk(
        "نام کاربری گلستان چیست؟\nبهصورت پیشفرض شماره دانشجویی",
        score=0.62,
    )
    ranked, _diagnostics = rank_dense_hits(
        query="نام کاربری گلستان چیست؟",
        chunks=[admin, username],
        top_k=2,
    )
    assert ranked[0].chunk_id == username.chunk_id


def test_login_steps_beat_admin_when_cosine_close() -> None:
    admin = _chunk(
        "در صورت بروز مشکل فنی در گلستان به کجا مراجعه کنیم؟\nبه ادمین سامانه گلستان دانشگاه",
        score=0.735,
    )
    login = _chunk(
        "چگونه وارد سامانه گلستان شویم؟\n"
        "از طریق سایت دانشگاه وارد بخش دانشگاه من شوید یا آدرس سامانه را وارد کنید."
        " سپس روی ورود به سیستم کلیک کنید.",
        score=0.70,
    )
    ranked, diagnostics = rank_dense_hits(
        query="چگونه وارد سامانه گلستان شویم؟",
        chunks=[admin, login],
        top_k=2,
    )
    assert ranked[0].chunk_id == login.chunk_id
    assert diagnostics.rankings[0].best_faq_question is not None


def test_distractor_penalty_on_forgot_password_for_initial_password_query() -> None:
    wrong = _chunk(
        "اگر رمز عبور را فراموش کنیم چه باید کرد؟\nتماس با کارشناس آموزش.",
        score=0.72,
    )
    correct = _chunk(
        "رمز عبور اولیه چیست؟\nکد ملی دانشجو.",
        score=0.70,
    )
    ranked, diagnostics = rank_dense_hits(
        query="رمز اولیه ورود چیست؟",
        chunks=[wrong, correct],
        top_k=2,
    )
    assert ranked[0].chunk_id == correct.chunk_id
    # Wrong neighbor should carry distractor and/or weaker FAQ overlap.
    wrong_diag = next(item for item in diagnostics.rankings if item.chunk_id == str(wrong.chunk_id))
    assert wrong_diag.adjusted_score <= diagnostics.rankings[0].adjusted_score


def test_ranking_is_deterministic_and_fast() -> None:
    chunks = [
        _chunk(f"سوال آزمایشی {index} چیست؟\nپاسخ {index}", score=0.5 + index * 0.01)
        for index in range(20)
    ]
    query = "سوال آزمایشی 7 چیست؟"
    started = time.perf_counter()
    first, _ = rank_dense_hits(query=query, chunks=chunks, top_k=5)
    mid = time.perf_counter()
    second, _ = rank_dense_hits(query=query, chunks=chunks, top_k=5)
    elapsed_ms = (mid - started) * 1000
    assert [item.chunk_id for item in first] == [item.chunk_id for item in second]
    assert elapsed_ms < 50.0  # pure lexical; far below 10% of typical retrieve latency


def test_golestan_offline_before_after_hit_at_1() -> None:
    """Simulated Golestan ranking cases with near-tied cosine (before = cosine order)."""
    cases = [
        {
            "query": "رمز عبور اولیه گلستان چیست؟",
            "gold_text": "رمز عبور اولیه گلستان چیست؟\nبهصورت پیشفرض کد ملی دانشجو است.",
            "distractors": [
                (
                    "اگر رمز عبور را فراموش کنیم چه باید کرد؟\nتماس با کارشناس آموزش.",
                    0.735,
                ),
                (
                    "مشکل فنی را به ادمین گزارش دهید.\nآقای کیانی",
                    0.65,
                ),
            ],
            "gold_cosine": 0.665,
        },
        {
            "query": "نام کاربری گلستان چیست؟",
            "gold_text": "نام کاربری گلستان چیست؟\nبهصورت پیشفرض شماره دانشجویی",
            "distractors": [
                (
                    "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟\nادمین کیانی",
                    0.67,
                ),
            ],
            "gold_cosine": 0.62,
        },
        {
            "query": "چگونه وارد سامانه گلستان شویم؟",
            "gold_text": (
                "چگونه وارد سامانه گلستان شویم؟\nاز سایت دانشگاه بخش دانشگاه من وارد شوید."
            ),
            "distractors": [
                (
                    "مشکل فنی سامانه گلستان را به چه کسی باید گزارش داد؟\nادمین",
                    0.735,
                ),
            ],
            "gold_cosine": 0.70,
        },
        {
            "query": "حذف اضطراری چیست و آیا قابل برگشت است؟",
            "gold_text": "حذف اضطراری چیست؟\nپس از تایید نهایی به هیچوجه قابل برگشت نیست.",
            "distractors": [
                (
                    "اگر پیشنیاز رعایت نشود چه میشود؟\nسیستم اجازه اخذ درس را نمیدهد.",
                    0.589,
                ),
            ],
            "gold_cosine": 0.55,
        },
        {
            "query": "درخواست انتقالی چگونه ثبت می‌شود؟",
            "gold_text": "درخواست انتقالی چگونه ثبت میشود؟\nفقط از طریق سامانه سجاد.",
            "distractors": [
                (
                    "دانشجوی مهمان چگونه انتخاب واحد انجام میدهد؟\nمستقیما در گلستان.",
                    0.54,
                ),
            ],
            "gold_cosine": 0.52,
        },
    ]

    before_hit1 = 0
    after_hit1 = 0
    before_mrr = 0.0
    after_mrr = 0.0
    for case in cases:
        gold = _chunk(case["gold_text"], case["gold_cosine"])
        distractors = [_chunk(text, score) for text, score in case["distractors"]]
        pool = [gold, *distractors]
        # Before: pure cosine order
        cosine_order = sorted(pool, key=lambda item: (-item.score, str(item.chunk_id)))
        if cosine_order[0].chunk_id == gold.chunk_id:
            before_hit1 += 1
        before_rank = next(
            index
            for index, item in enumerate(cosine_order, start=1)
            if item.chunk_id == gold.chunk_id
        )
        before_mrr += 1.0 / before_rank

        ranked, _ = rank_dense_hits(query=case["query"], chunks=pool, top_k=5)
        if ranked[0].chunk_id == gold.chunk_id:
            after_hit1 += 1
        after_rank = next(
            index for index, item in enumerate(ranked, start=1) if item.chunk_id == gold.chunk_id
        )
        after_mrr += 1.0 / after_rank

    n = len(cases)
    assert after_hit1 > before_hit1
    assert (after_mrr / n) > (before_mrr / n)
    assert after_hit1 == n
