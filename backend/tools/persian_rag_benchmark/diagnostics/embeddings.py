"""Embedding diagnostics for Persian semantic search."""

from __future__ import annotations

import math
from collections import defaultdict
from statistics import mean

from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.core.config.settings import Settings
from tools.persian_rag_benchmark.models import QuestionRunResult


async def diagnose_embeddings(
    results: list[QuestionRunResult],
    *,
    settings: Settings,
    embedding_provider: EmbeddingProvider | None,
    sample_limit: int = 40,
) -> dict[str, object]:
    scores: list[float] = []
    for result in results:
        for evidence in result.retrieved:
            scores.append(evidence.score)

    histogram = _histogram(scores)
    parent_groups: dict[str, list[QuestionRunResult]] = defaultdict(list)
    for result in results:
        key = result.parent_question_id or result.question_id
        parent_groups[key].append(result)

    instability: list[dict[str, object]] = []
    for parent_id, group in parent_groups.items():
        top_chunks = {item.retrieved[0].chunk_id for item in group if item.retrieved}
        if len(top_chunks) > 1:
            instability.append(
                {
                    "parent_question_id": parent_id,
                    "distinct_top_chunks": sorted(top_chunks),
                    "variant_count": len(group),
                }
            )

    nearest: list[dict[str, object]] = []
    duplicate_rate: float | None = None
    if embedding_provider is not None and results:
        texts = [item.normalized_question for item in results[:sample_limit]]
        vectors = await embedding_provider.embed_texts(texts)
        nearest = _nearest_pairs(texts, vectors, limit=10)
        duplicate_rate = _duplicate_vector_rate(vectors)

    return {
        "embedding_backend": settings.embedding_backend,
        "embedding_model_key": settings.embedding_model_key,
        "embedding_dimensions": settings.embedding_dimensions,
        "score_mean": mean(scores) if scores else None,
        "score_min": min(scores) if scores else None,
        "score_max": max(scores) if scores else None,
        "similarity_histogram": histogram,
        "duplicate_vector_rate": duplicate_rate,
        "nearest_neighbours": nearest,
        "robustness_top_chunk_instability": instability[:20],
        "instability_rate": (len(instability) / len(parent_groups) if parent_groups else None),
    }


def _histogram(scores: list[float], *, buckets: int = 10) -> list[dict[str, object]]:
    if not scores:
        return []
    low, high = min(scores), max(scores)
    if math.isclose(low, high):
        return [{"start": low, "end": high, "count": len(scores)}]
    width = (high - low) / buckets
    counts = [0] * buckets
    for score in scores:
        index = min(buckets - 1, int((score - low) / width))
        counts[index] += 1
    return [
        {
            "start": low + index * width,
            "end": low + (index + 1) * width,
            "count": counts[index],
        }
        for index in range(buckets)
    ]


def _cosine(left: list[float], right: list[float]) -> float:
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    norm_l = math.sqrt(sum(a * a for a in left)) or 1e-9
    norm_r = math.sqrt(sum(b * b for b in right)) or 1e-9
    return dot / (norm_l * norm_r)


def _nearest_pairs(
    texts: list[str],
    vectors: list[list[float]],
    *,
    limit: int,
) -> list[dict[str, object]]:
    pairs: list[tuple[float, int, int]] = []
    for i in range(len(vectors)):
        for j in range(i + 1, len(vectors)):
            pairs.append((_cosine(vectors[i], vectors[j]), i, j))
    pairs.sort(reverse=True)
    out: list[dict[str, object]] = []
    for score, i, j in pairs[:limit]:
        out.append(
            {
                "left": texts[i][:120],
                "right": texts[j][:120],
                "cosine": score,
            }
        )
    return out


def _duplicate_vector_rate(vectors: list[list[float]]) -> float | None:
    if not vectors:
        return None
    rounded = [tuple(round(value, 6) for value in vector) for vector in vectors]
    unique = len(set(rounded))
    return 1.0 - (unique / len(rounded))
