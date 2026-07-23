"""Unit tests for BM25 and hybrid RRF fusion (RC3.5)."""

from __future__ import annotations

import uuid

from rag_enterprise.retrieval.bm25 import BM25Index, LexicalDocument, tokenize_lexical
from rag_enterprise.retrieval.hybrid import (
    apply_persian_bm25_boosts,
    blend_cosine_with_rrf,
    fuse_dense_and_bm25,
    reciprocal_rank_fusion,
)
from rag_enterprise.retrieval.models import RetrievedChunk
from rag_enterprise.retrieval.ranking import rank_dense_hits


def _doc(text: str, *, heading: str | None = None) -> LexicalDocument:
    chunk_id = str(uuid.uuid4())
    return LexicalDocument(
        chunk_id=chunk_id,
        document_id=str(uuid.uuid4()),
        document_version_id=str(uuid.uuid4()),
        knowledge_base_id=str(uuid.uuid4()),
        chunk_index=0,
        start_char=0,
        end_char=len(text),
        heading=heading,
        language="fa",
        text=text,
        tokens=tuple(tokenize_lexical(text if heading is None else f"{heading}\n{text}")),
    )


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
        heading=None,
        language="fa",
    )


def test_tokenize_preserves_persian_yeh_kaf_and_digits() -> None:
    tokens = tokenize_lexical("کد ملی ۱۴ و یوزر Google Chrome")
    assert "کد" in tokens
    assert "ملی" in tokens
    assert "14" in tokens
    assert "google" in tokens
    assert "chrome" in tokens


def test_bm25_prefers_exact_initial_password_faq() -> None:
    wrong = _doc("اگر رمز عبور را فراموش کنیم چه باید کرد؟\nبا کارشناس آموزش تماس بگیرید.")
    correct = _doc("رمز عبور اولیه گلستان چیست؟\nبهصورت پیشفرض کد ملی دانشجو است.")
    index = BM25Index([wrong, correct])
    hits = index.search(tokenize_lexical("رمز عبور اولیه گلستان چیست؟"), top_k=2)
    assert hits
    assert hits[0].chunk_id == correct.chunk_id


def test_persian_boost_promotes_exact_faq_question() -> None:
    wrong = _doc("اگر رمز را فراموش کردم چه کنم؟\nریست توسط آموزش.")
    correct = _doc("رمز اولیه سامانه چیست؟\nکد ملی.")
    index = BM25Index([wrong, correct])
    raw = index.search(tokenize_lexical("رمز اولیه سامانه چیست؟"), top_k=2)
    boosted = apply_persian_bm25_boosts(
        query="رمز اولیه سامانه چیست؟",
        index=index,
        hits=raw,
    )
    assert boosted[0].chunk_id == correct.chunk_id


def test_bm25_matches_browser_name() -> None:
    other = _doc("پرداخت شهریه از بخش پرداختهای الکترونیکی است.")
    browser = _doc("بهترین مرورگر برای گلستان چیست؟\nGoogle Chrome یا Firefox.")
    index = BM25Index([other, browser])
    hits = index.search(tokenize_lexical("بهترین مرورگر Google Chrome"), top_k=2)
    assert hits[0].chunk_id == browser.chunk_id


def test_bm25_matches_report_number() -> None:
    grades = _doc("نمرات ترمی از اطلاعات جامع مشاهده می‌شود.")
    weekly = _doc("چگونه برنامه هفتگی را مشاهده کنیم؟\nاز گزارش 88 یا گزارش 78.")
    index = BM25Index([grades, weekly])
    hits = index.search(tokenize_lexical("برنامه هفتگی گزارش 88"), top_k=2)
    assert hits[0].chunk_id == weekly.chunk_id


def test_rrf_promotes_lexical_winner_over_dense_distractor() -> None:
    dense = ["dense-wrong", "dense-ok"]
    bm25 = ["dense-ok", "dense-wrong"]
    fused = reciprocal_rank_fusion([dense, bm25], k=60)
    assert fused[0][0] == "dense-ok"


def test_hybrid_then_rc32_recovers_near_duplicate_faq() -> None:
    wrong = _chunk(
        "اگر رمز عبور را فراموش کنیم چه باید کرد؟\nکارشناس آموزش دانشکده.",
        score=0.74,
    )
    correct = _chunk(
        "رمز عبور اولیه گلستان چیست؟\nکد ملی دانشجو.",
        score=0.61,
    )
    dense_ids = [str(wrong.chunk_id), str(correct.chunk_id)]
    # BM25 finds the exact FAQ first; dense alone would prefer the distractor.
    bm25_ids = [str(correct.chunk_id)]
    fused_ids, rrf_scores, diagnostics = fuse_dense_and_bm25(
        dense_ids=dense_ids,
        bm25_ids=bm25_ids,
        dense_scores={dense_ids[0]: 0.74, dense_ids[1]: 0.61},
        bm25_scores={bm25_ids[0]: 12.0},
    )
    assert fused_ids[0] == str(correct.chunk_id)
    assert diagnostics.rrf_top[0].chunk_id == str(correct.chunk_id)

    max_rrf = max(rrf_scores.values())
    by_id = {str(wrong.chunk_id): wrong, str(correct.chunk_id): correct}
    fused_chunks = [
        by_id[chunk_id].model_copy(
            update={
                "score": blend_cosine_with_rrf(
                    cosine_score=float(by_id[chunk_id].score),
                    rrf_score=rrf_scores[chunk_id],
                    max_rrf_score=max_rrf,
                )
            }
        )
        for chunk_id in fused_ids
    ]
    ranked, _ = rank_dense_hits(
        query="رمز عبور اولیه گلستان چیست؟",
        chunks=fused_chunks,
        top_k=2,
    )
    assert ranked[0].chunk_id == correct.chunk_id


def test_faq_segment_scoring_prefers_definition_over_related_penalty_faq() -> None:
    related = _doc(
        "اگر پیشنیاز رعایت نشود چه میشود؟\nسیستم اجازه اخذ درس را نمیدهد.\n"
        "تداخل دروس یعنی چه؟\nهمپوشانی زمانی کلاسها."
    )
    definition = _doc("پیشنیاز دروس یعنی چه؟\nدرسی که باید قبل از اخذ یک درس دیگر گذرانده شود.")
    index = BM25Index([related, definition])
    query = "پیش‌نیاز دروس یعنی چه؟"
    raw = index.search(tokenize_lexical(query), top_k=2)
    hits = apply_persian_bm25_boosts(query=query, index=index, hits=raw)
    assert hits[0].chunk_id == definition.chunk_id


def test_course_code_and_password_terms() -> None:
    leave = _doc("مرخصی استحقاقی ۲۰ روز است.")
    password = _doc("رمز عبور اولیه چیست؟\nکد ملی.")
    index = BM25Index([leave, password])
    hits = index.search(tokenize_lexical("رمز عبور اولیه کد ملی"), top_k=2)
    assert hits[0].chunk_id == password.chunk_id
