"""Metric trust labels for the Persian RAG benchmark."""

from __future__ import annotations

from enum import StrEnum


class MetricTrust(StrEnum):
    """How a reported value was obtained."""

    MEASURED = "Measured"
    DERIVED = "Derived"
    ESTIMATED = "Estimated"
    HEURISTIC = "Heuristic"


class GoldProvenance(StrEnum):
    """Origin of ground-truth labels — controls Measured eligibility."""

    CURATED_EXTERNAL = "curated_external"
    AUTO_CORPUS_PROBE = "auto_corpus_probe"


class EvaluationCohort(StrEnum):
    """Never mix cohorts in aggregate metrics."""

    BASELINE = "baseline"
    ROBUSTNESS = "robustness"


# Human-readable computation notes for the Trust Report / HTML.
METRIC_DEFINITIONS: dict[str, dict[str, str]] = {
    "hit_at_k": {
        "trust": MetricTrust.MEASURED.value,
        "definition": (
            "Hit@k = 1 if at least one expected chunk_id appears in the top-k "
            "retrieved chunk_ids from RetrievalService; else 0. Mean over questions."
        ),
    },
    "recall_at_k": {
        "trust": MetricTrust.MEASURED.value,
        "definition": (
            "Recall@k = |expected ∩ retrieved_top_k| / |expected|. "
            "For a single expected chunk this equals Hit@k. Mean over questions."
        ),
    },
    "precision_at_k": {
        "trust": MetricTrust.MEASURED.value,
        "definition": (
            "Precision@k = |expected ∩ retrieved_top_k| / k. "
            "Denominator is always k (configured top_k), never |retrieved|."
        ),
    },
    "mrr": {
        "trust": MetricTrust.MEASURED.value,
        "definition": (
            "MRR = mean over questions of 1/rank of the first expected chunk in "
            "retrieval results; 0 if none appear."
        ),
    },
    "retrieval_score": {
        "trust": MetricTrust.MEASURED.value,
        "definition": "Cosine/similarity score field returned by RetrievalService.retrieve.",
    },
    "generated_answer": {
        "trust": MetricTrust.MEASURED.value,
        "definition": "generation.answer from GenerationService.generate.",
    },
    "citations": {
        "trust": MetricTrust.MEASURED.value,
        "definition": "chunk_id list from GenerationService.generate citations.",
    },
    "exact_match": {
        "trust": MetricTrust.DERIVED.value,
        "definition": (
            "True iff digit-normalized, whitespace-collapsed lowercase gold == predicted."
        ),
    },
    "citation_accuracy": {
        "trust": MetricTrust.MEASURED.value,
        "definition": "True iff expected_chunk_id is in the citation chunk_id list.",
    },
    "numeric_accuracy": {
        "trust": MetricTrust.DERIVED.value,
        "definition": (
            "|latin_digits(gold numbers) ∩ latin_digits(pred numbers)| / |gold numbers|; "
            "None if gold has no numbers."
        ),
    },
    "lexical_overlap": {
        "trust": MetricTrust.HEURISTIC.value,
        "definition": (
            "Heuristic: Jaccard overlap of whitespace tokens after digit/whitespace normalize. "
            "Not semantic similarity."
        ),
    },
    "heuristic_fluency_estimate": {
        "trust": MetricTrust.HEURISTIC.value,
        "definition": (
            "Heuristic: Persian-script character ratio × spacing penalty. "
            "Not a linguistic fluency score."
        ),
    },
    "entity_match_estimate": {
        "trust": MetricTrust.HEURISTIC.value,
        "definition": "Heuristic: lexical overlap reused for responsibility/permission categories.",
    },
    "procedure_match_estimate": {
        "trust": MetricTrust.HEURISTIC.value,
        "definition": "Heuristic: lexical overlap reused for procedure/multi_step categories.",
    },
    "groundedness_estimate": {
        "trust": MetricTrust.HEURISTIC.value,
        "definition": (
            "Heuristic: citation_accuracy AND lexical_overlap ≥ 0.15. Not Feature-007 is_grounded."
        ),
    },
    "embedding_nearest_neighbours": {
        "trust": MetricTrust.MEASURED.value,
        "definition": (
            "Pairwise cosine on vectors from EmbeddingProvider.embed_texts(query sample)."
        ),
    },
    "duplicate_vector_rate": {
        "trust": MetricTrust.MEASURED.value,
        "definition": "1 − unique_rounded_vectors / n on sampled query embeddings.",
    },
    "pass_rate": {
        "trust": MetricTrust.DERIVED.value,
        "definition": (
            "Fraction of questions with Measured retrieval hit "
            "(and, if generation ran, no heuristic hallucination flag)."
        ),
    },
}
