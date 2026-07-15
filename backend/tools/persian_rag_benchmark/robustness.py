"""Persian robustness question variants."""

from __future__ import annotations

import random
import re

from tools.persian_rag_benchmark.models import GroundTruthQuestion, RobustnessKind
from tools.persian_rag_benchmark.persian_text import (
    add_noisy_punctuation,
    arabic_yeh_kaf_variant,
    collapse_whitespace,
    insert_halfspaces_naive,
    remove_halfspaces,
    strip_persian_punctuation,
    to_arabic_indic_digits,
    to_latin_digits,
    to_persian_digits,
)

_SYNONYMS: tuple[tuple[str, str], ...] = (
    ("کارکنان", "پرسنل"),
    ("پرسنل", "کارمندان"),
    ("کارمند", "پرسنل"),
    ("مرخصی", "مرخصی استحقاقی"),
    ("سازمان", "شرکت"),
    ("مدیر", "سرپرست"),
    ("روز کاری", "روز کاری اداری"),
)

_FORMAL_PREFIX = "خواهشمند است مشخص فرمایید که "
_INFORMAL_SUFFIX = "؟"


def expand_robustness_variants(
    questions: list[GroundTruthQuestion],
    *,
    max_variants_per_question: int = 8,
    seed: int = 42,
) -> list[GroundTruthQuestion]:
    """Attach Persian surface/paraphrase variants for each base question."""
    rng = random.Random(seed)
    expanded: list[GroundTruthQuestion] = []
    for question in questions:
        expanded.append(question)
        variants = _build_variants(question, rng=rng)
        rng.shuffle(variants)
        for variant in variants[:max_variants_per_question]:
            expanded.append(variant)
    return expanded


def _build_variants(
    question: GroundTruthQuestion,
    *,
    rng: random.Random,
) -> list[GroundTruthQuestion]:
    text = question.question
    builders: list[tuple[RobustnessKind, str]] = [
        (RobustnessKind.PARAPHRASE, _paraphrase(text, rng)),
        (RobustnessKind.FORMAL, f"{_FORMAL_PREFIX}{text.rstrip('؟')}{_INFORMAL_SUFFIX}"),
        (RobustnessKind.INFORMAL, _informalize(text)),
        (RobustnessKind.SYNONYM, _apply_synonym(text, rng)),
        (RobustnessKind.ARABIC_YEH_KAF, arabic_yeh_kaf_variant(text)),
        (RobustnessKind.HALFSPACE, insert_halfspaces_naive(remove_halfspaces(text))),
        (RobustnessKind.DIGIT_LATIN, to_latin_digits(text)),
        (RobustnessKind.DIGIT_PERSIAN, to_persian_digits(text)),
        (RobustnessKind.DIGIT_ARABIC_INDIC, to_arabic_indic_digits(text)),
        (RobustnessKind.PUNCTUATION, add_noisy_punctuation(text)),
        (RobustnessKind.NO_PUNCTUATION, strip_persian_punctuation(text)),
        (RobustnessKind.WHITESPACE, collapse_whitespace(re.sub(r"\s", "  ", text))),
        (RobustnessKind.SPELLING, _light_spelling_noise(text, rng)),
    ]

    results: list[GroundTruthQuestion] = []
    for kind, variant_text in builders:
        if not variant_text or variant_text.strip() == text.strip():
            continue
        results.append(
            question.model_copy(
                update={
                    "id": f"{question.id}__{kind.value}",
                    "question": variant_text,
                    "parent_question_id": question.id,
                    "robustness_kind": kind,
                    "tags": sorted(set(question.tags + ["robustness", kind.value])),
                    "notes": f"robustness_of={question.id};kind={kind.value}",
                    "gold_provenance": question.gold_provenance,
                    "eligible_for_measured_retrieval": (question.eligible_for_measured_retrieval),
                }
            )
        )
    return results


def _paraphrase(text: str, rng: random.Random) -> str:
    options = (
        text.replace("چند", "چه تعداد", 1),
        text.replace("چیست", "چه می‌باشد", 1),
        text.replace("چگونه", "به چه صورت", 1),
        f"لطفاً توضیح دهید: {text}",
    )
    return rng.choice(options)


def _informalize(text: str) -> str:
    softened = text.replace("می‌باشد", "هست").replace("است؟", "ه؟")
    if softened.endswith("؟"):
        return softened
    return f"{softened}؟"


def _apply_synonym(text: str, rng: random.Random) -> str:
    candidates = [(src, dst) for src, dst in _SYNONYMS if src in text]
    if not candidates:
        return text
    src, dst = rng.choice(candidates)
    return text.replace(src, dst, 1)


def _light_spelling_noise(text: str, rng: random.Random) -> str:
    # Mild orthographic variation common in Persian typing (no scramble).
    replacements = (
        ("می‌", "مي‌"),
        ("ها", " های"),
        ("است", " هست"),
    )
    src, dst = rng.choice(replacements)
    if src in text:
        return text.replace(src, dst, 1)
    return f"{text} "
