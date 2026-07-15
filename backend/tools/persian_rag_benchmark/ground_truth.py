"""Generate high-quality Persian ground-truth questions from indexed chunks."""

from __future__ import annotations

import hashlib
import random
import re
from collections import defaultdict

from tools.persian_rag_benchmark.models import (
    ChunkSnapshot,
    Difficulty,
    GroundTruthQuestion,
    QuestionCategory,
)
from tools.persian_rag_benchmark.persian_text import (
    extract_keywords,
    extract_numbers,
    split_persian_sentences,
)

# Balanced category rotation for 40–60 questions per document.
_CATEGORY_CYCLE: tuple[QuestionCategory, ...] = (
    QuestionCategory.FACTUAL,
    QuestionCategory.POLICY_LOOKUP,
    QuestionCategory.NUMERICAL,
    QuestionCategory.DATE,
    QuestionCategory.DEFINITION,
    QuestionCategory.PROCEDURE,
    QuestionCategory.EXCEPTION,
    QuestionCategory.COMPARISON,
    QuestionCategory.YES_NO,
    QuestionCategory.LIST,
    QuestionCategory.RESPONSIBILITY,
    QuestionCategory.PERMISSION,
    QuestionCategory.RESTRICTION,
    QuestionCategory.DEADLINE,
    QuestionCategory.MULTI_STEP,
    QuestionCategory.MULTI_HOP,
    QuestionCategory.CROSS_SECTION,
)


def generate_ground_truth(
    chunks: list[ChunkSnapshot],
    *,
    knowledge_base_id: str,
    questions_per_document_min: int = 40,
    questions_per_document_max: int = 60,
    seed: int = 42,
) -> list[GroundTruthQuestion]:
    """Build 40–60 natural Persian questions per document from chunk text."""
    by_document: dict[str, list[ChunkSnapshot]] = defaultdict(list)
    for chunk in chunks:
        by_document[str(chunk.document_id)].append(chunk)

    results: list[GroundTruthQuestion] = []
    for document_id, doc_chunks in sorted(by_document.items()):
        rng = random.Random(f"{seed}:{document_id}")
        target = rng.randint(questions_per_document_min, questions_per_document_max)
        generated = _generate_for_document(
            doc_chunks,
            knowledge_base_id=knowledge_base_id,
            target=target,
            rng=rng,
        )
        results.extend(generated)
    return results


def _generate_for_document(
    chunks: list[ChunkSnapshot],
    *,
    knowledge_base_id: str,
    target: int,
    rng: random.Random,
) -> list[GroundTruthQuestion]:
    candidates: list[GroundTruthQuestion] = []
    ordered = sorted(chunks, key=lambda item: item.sequence_number)
    for index, chunk in enumerate(ordered):
        sentences = split_persian_sentences(chunk.text)
        for sentence in sentences:
            if len(sentence) < 25:
                continue
            for category in _CATEGORY_CYCLE:
                question = _try_build_question(
                    sentence=sentence,
                    chunk=chunk,
                    peer_chunks=ordered,
                    chunk_index=index,
                    category=category,
                    knowledge_base_id=knowledge_base_id,
                    rng=rng,
                )
                if question is not None:
                    candidates.append(question)

    # Deduplicate by question text, then sample to target with category balance.
    unique: list[GroundTruthQuestion] = []
    seen_questions: set[str] = set()
    for item in candidates:
        key = item.question.strip()
        if key in seen_questions:
            continue
        seen_questions.add(key)
        unique.append(item)

    if not unique:
        # Fallback: force factual questions from chunk heads.
        for chunk in ordered:
            passage = chunk.text[:280].strip()
            if len(passage) < 20:
                continue
            unique.append(
                _make_question(
                    question=(
                        f"بر اساس سند، دربارهٔ موضوع زیر چه اطلاعاتی آمده است: {passage[:48]}…؟"
                    ),
                    answer=passage,
                    passage=passage,
                    chunk=chunk,
                    category=QuestionCategory.FACTUAL,
                    difficulty=Difficulty.EASY,
                    knowledge_base_id=knowledge_base_id,
                    keywords=extract_keywords(passage),
                )
            )

    selected = _balanced_sample(unique, target=target, rng=rng)
    # Stable ids
    stamped: list[GroundTruthQuestion] = []
    for ordinal, item in enumerate(selected, start=1):
        stamped.append(
            item.model_copy(
                update={
                    "id": f"fa-{str(item.expected_document_id)[:8]}-{ordinal:03d}",
                    "tags": sorted(set(item.tags + [item.category.value, "persian_benchmark"])),
                }
            )
        )
    return stamped


def _balanced_sample(
    items: list[GroundTruthQuestion],
    *,
    target: int,
    rng: random.Random,
) -> list[GroundTruthQuestion]:
    if len(items) <= target:
        # Pad by paraphrasing existing with slight difficulty shift if too few.
        while len(items) < target and items:
            base = rng.choice(items)
            items.append(
                base.model_copy(
                    update={
                        "question": _paraphrase_soft(base.question, rng),
                        "difficulty": Difficulty.MEDIUM,
                        "notes": (base.notes or "") + ";padded",
                    }
                )
            )
        return items[:target]

    by_cat: dict[QuestionCategory, list[GroundTruthQuestion]] = defaultdict(list)
    for item in items:
        by_cat[item.category].append(item)
    for bucket in by_cat.values():
        rng.shuffle(bucket)

    selected: list[GroundTruthQuestion] = []
    categories = list(_CATEGORY_CYCLE)
    while len(selected) < target:
        progressed = False
        for category in categories:
            bucket = by_cat.get(category) or []
            if not bucket:
                continue
            selected.append(bucket.pop())
            progressed = True
            if len(selected) >= target:
                break
        if not progressed:
            remainder = [item for bucket in by_cat.values() for item in bucket]
            rng.shuffle(remainder)
            selected.extend(remainder[: target - len(selected)])
            break
    return selected


def _try_build_question(
    *,
    sentence: str,
    chunk: ChunkSnapshot,
    peer_chunks: list[ChunkSnapshot],
    chunk_index: int,
    category: QuestionCategory,
    knowledge_base_id: str,
    rng: random.Random,
) -> GroundTruthQuestion | None:
    numbers = extract_numbers(sentence)
    keywords = extract_keywords(sentence)
    topic = keywords[0] if keywords else "این موضوع"
    passage = sentence if len(sentence) >= 40 else chunk.text[:400]
    citation = passage[:220]

    if category == QuestionCategory.NUMERICAL:
        if not numbers:
            return None
        number = numbers[0]
        return _make_question(
            question=f"طبق متن، مقدار عددی مرتبط با «{topic}» چقدر است؟",
            answer=f"بر اساس سند، مقدار ذکرشده {number} است.",
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.EASY,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.DATE:
        if not re.search(r"(روز|ماه|سال|مهلت|تاریخ|شنب|جمعه)", sentence):
            return None
        return _make_question(
            question=f"زمان‌بندی یا مهلت مربوط به «{topic}» در سند چگونه بیان شده است؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.MEDIUM,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.YES_NO:
        if "نمی" in sentence or "نیست" in sentence or "مجاز" in sentence or "الزامی" in sentence:
            polarity = "خیر" if any(tok in sentence for tok in ("نیست", "نمی", "ممنوع")) else "بله"
            return _make_question(
                question=f"آیا طبق سند، «{topic}» مجاز یا الزامی است؟",
                answer=f"{polarity}. {passage}",
                passage=passage,
                chunk=chunk,
                category=category,
                difficulty=Difficulty.MEDIUM,
                knowledge_base_id=knowledge_base_id,
                keywords=keywords,
                citation=citation,
            )
        return None

    if category == QuestionCategory.DEFINITION:
        if "عبارت است" in sentence or "به معنای" in sentence or "تعریف" in sentence:
            return _make_question(
                question=f"تعریف «{topic}» در این سند چیست؟",
                answer=passage,
                passage=passage,
                chunk=chunk,
                category=category,
                difficulty=Difficulty.EASY,
                knowledge_base_id=knowledge_base_id,
                keywords=keywords,
                citation=citation,
            )
        return _make_question(
            question=f"سند «{topic}» را چگونه توصیف می‌کند؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.EASY,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.PROCEDURE or category == QuestionCategory.MULTI_STEP:
        procedure_tokens = ("باید", "لازم", "مراحل", "ابتدا", "سپس")
        missing_procedure_cue = not any(tok in sentence for tok in procedure_tokens)
        if missing_procedure_cue and category == QuestionCategory.MULTI_STEP:
            return None
        return _make_question(
            question=f"مراحل انجام «{topic}» طبق سند چیست؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=(
                Difficulty.HARD if category == QuestionCategory.MULTI_STEP else Difficulty.MEDIUM
            ),
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.EXCEPTION or category == QuestionCategory.RESTRICTION:
        if not any(tok in sentence for tok in ("استثنا", "مگر", "فقط", "حداکثر", "ممنوع", "نباید")):
            return None
        return _make_question(
            question=f"چه محدودیت یا استثنایی دربارهٔ «{topic}» آمده است؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.HARD,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.PERMISSION:
        if not any(tok in sentence for tok in ("مجاز", "اجازه", "می‌توان", "اختیار")):
            return None
        return _make_question(
            question=f"چه مجوزهایی برای «{topic}» در سند ذکر شده است؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.MEDIUM,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.RESPONSIBILITY:
        if not any(tok in sentence for tok in ("مسئول", "مدیر", "منابع انسانی", "کارمند", "واحد")):
            return None
        return _make_question(
            question=f"مسئولیت مرتبط با «{topic}» بر عهده کیست؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.MEDIUM,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.DEADLINE:
        if not any(tok in sentence for tok in ("حداکثر", "مهلت", "ظرف", "روز کاری", "موعد")):
            return None
        return _make_question(
            question=f"مهلت مربوط به «{topic}» چقدر است؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.EASY,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.LIST:
        if "،" not in sentence and "و" not in sentence:
            return None
        return _make_question(
            question=f"فهرست موارد مرتبط با «{topic}» در سند چیست؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.MEDIUM,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.COMPARISON:
        if "نسبت" not in sentence and "در مقایسه" not in sentence and "یا" not in sentence:
            return None
        return _make_question(
            question=f"تفاوت یا مقایسهٔ بیان‌شده دربارهٔ «{topic}» چیست؟",
            answer=passage,
            passage=passage,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.HARD,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=citation,
        )

    if category == QuestionCategory.MULTI_HOP or category == QuestionCategory.CROSS_SECTION:
        if chunk_index + 1 >= len(peer_chunks):
            return None
        other = peer_chunks[chunk_index + 1]
        combined = f"{passage}\n{other.text[:220]}"
        return _make_question(
            question=f"با توجه به بخش‌های مرتبط سند، دربارهٔ «{topic}» چه نتیجه‌ای گرفته می‌شود؟",
            answer=combined,
            passage=combined,
            chunk=chunk,
            category=category,
            difficulty=Difficulty.HARD,
            knowledge_base_id=knowledge_base_id,
            keywords=keywords,
            citation=passage[:180],
            notes=f"multi_section_with_chunk={other.chunk_id}",
        )

    # factual / policy_lookup defaults
    templates = [
        f"طبق سند، دربارهٔ «{topic}» چه مطلبی آمده است؟",
        f"سیاست مرتبط با «{topic}» چگونه بیان شده است؟",
        f"متن سیاست در مورد «{topic}» چه می‌گوید؟",
    ]
    question = rng.choice(templates)
    return _make_question(
        question=question,
        answer=passage,
        passage=passage,
        chunk=chunk,
        category=category,
        difficulty=Difficulty.EASY,
        knowledge_base_id=knowledge_base_id,
        keywords=keywords,
        citation=citation,
    )


def _make_question(
    *,
    question: str,
    answer: str,
    passage: str,
    chunk: ChunkSnapshot,
    category: QuestionCategory,
    difficulty: Difficulty,
    knowledge_base_id: str,
    keywords: list[str],
    citation: str | None = None,
    notes: str | None = None,
) -> GroundTruthQuestion:
    digest = hashlib.sha1(f"{chunk.chunk_id}:{question}".encode()).hexdigest()[:10]
    return GroundTruthQuestion(
        id=f"tmp-{digest}",
        question=question,
        gold_answer=answer.strip(),
        supporting_passage=passage.strip(),
        expected_citation_text=(citation or passage[:220]).strip(),
        expected_document_id=str(chunk.document_id),
        expected_chunk_id=str(chunk.chunk_id),
        knowledge_base_id=knowledge_base_id,
        category=category,
        difficulty=difficulty,
        keywords=keywords,
        tags=[category.value, "fa"],
        language="fa",
        notes=notes,
    )


def _paraphrase_soft(question: str, rng: random.Random) -> str:
    prefixes = ("بر اساس سند، ", "طبق سیاست، ", "با توجه به متن، ")
    if question.startswith(prefixes):
        return question
    return f"{rng.choice(prefixes)}{question.lstrip()}"
