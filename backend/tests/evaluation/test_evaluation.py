"""Evaluation package unit and component tests."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from pathlib import Path

import pytest

from rag_enterprise.evaluation.dataset import load_dataset
from rag_enterprise.evaluation.exceptions import DatasetValidationError
from rag_enterprise.evaluation.metrics import (
    abstention_precision,
    abstention_recall,
    aggregate_metrics,
    citation_precision,
    evaluate_thresholds,
    is_citation_accurate,
    mean_reciprocal_rank,
    recall_at_k,
)
from rag_enterprise.evaluation.models import (
    CitationRef,
    Difficulty,
    EvaluationStatus,
    ExperimentConfig,
    ExperimentThresholds,
    QuestionLanguage,
    QuestionOutcome,
)
from rag_enterprise.evaluation.service import EvaluationService
from rag_enterprise.evaluation.storage import ExperimentStorage
from rag_enterprise.generation.models import Citation, GenerationResult, GenerationStatus
from rag_enterprise.retrieval.models import RetrievedChunk, SearchRequest, SearchResponse

KB_ID = "018f0000-0000-7000-8000-0000000000b1"
CHUNK_A = "018f0000-0000-7000-8000-0000000000c1"
CHUNK_B = "018f0000-0000-7000-8000-0000000000c2"
DOC_A = "018f0000-0000-7000-8000-0000000000d1"


def _write_dataset(
    root: Path,
    *,
    questions: list[dict[str, object]],
    question_count: int | None = None,
) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_id": "kb-hr-fa-smoke",
        "dataset_version": "1.0.0",
        "knowledge_base_id": KB_ID,
        "question_count": question_count if question_count is not None else len(questions),
        "languages": ["fa", "en"],
        "created_at": "2026-07-14T00:00:00Z",
        "notes": "test fixture",
    }
    (root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    lines = [json.dumps(q, ensure_ascii=False) for q in questions]
    (root / "dataset.jsonl").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return root


def _answerable(qid: str = "hr-leave-001", *, language: str = "fa") -> dict[str, object]:
    return {
        "id": qid,
        "question": "مرخصی سالانه چند روز است؟",
        "expected_answer": "مرخصی سالانه ۲۰ روز کاری است.",
        "expected_citations": [{"chunk_id": CHUNK_A, "document_id": DOC_A}],
        "knowledge_base_id": KB_ID,
        "difficulty": "easy",
        "language": language,
        "tags": ["leave", "hr"],
        "expect_abstention": False,
    }


def _abstain(qid: str = "hr-unknown-001") -> dict[str, object]:
    return {
        "id": qid,
        "question": "قیمت سهام شرکت چقدر است؟",
        "expected_answer": "",
        "expected_citations": [],
        "knowledge_base_id": KB_ID,
        "difficulty": "easy",
        "language": "fa",
        "tags": ["abstain"],
        "expect_abstention": True,
    }


@dataclass
class FakeRetrieval:
    by_query: dict[str, list[RetrievedChunk]] = field(default_factory=dict)
    default_chunks: list[RetrievedChunk] = field(default_factory=list)

    async def retrieve(self, request: SearchRequest) -> SearchResponse:
        chunks = self.by_query.get(request.query_text, self.default_chunks)
        return SearchResponse(
            query_text=request.query_text,
            knowledge_base_id=request.knowledge_base_id,
            embedding_model_id=uuid.uuid4(),
            top_k=request.top_k,
            results=chunks[: request.top_k],
            result_count=min(len(chunks), request.top_k),
        )


@dataclass
class FakeGeneration:
    results: dict[str, GenerationResult] = field(default_factory=dict)
    default: GenerationResult | None = None

    async def generate(self, request: object) -> GenerationResult:
        question = getattr(request, "question", "")
        if question in self.results:
            return self.results[question]
        assert self.default is not None
        return self.default


def _chunk(chunk_id: str, *, score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.UUID(chunk_id),
        document_id=uuid.UUID(DOC_A),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.UUID(KB_ID),
        score=score,
        text="Annual leave is 20 working days.",
        chunk_index=0,
        start_char=0,
        end_char=30,
    )


def _citation(chunk_id: str) -> Citation:
    return Citation(
        chunk_id=uuid.UUID(chunk_id),
        document_id=uuid.UUID(DOC_A),
        document_version_id=uuid.uuid4(),
        rank=1,
        relevance_score=0.9,
        excerpt="Annual leave is 20 working days.",
        marker="[1]",
    )


def _completed(chunk_id: str = CHUNK_A) -> GenerationResult:
    chunk = _chunk(chunk_id)
    return GenerationResult(
        status=GenerationStatus.COMPLETED,
        answer="مرخصی سالانه ۲۰ روز کاری است. [1]",
        citations=[_citation(chunk_id)],
        retrieved_chunks=[chunk],
        retrieved_chunk_ids=[uuid.UUID(chunk_id)],
        model_key="echo",
        prompt_template_version="v1",
    )


def _abstained() -> GenerationResult:
    return GenerationResult(
        status=GenerationStatus.ABSTAINED,
        answer="I do not have enough evidence.",
        abstention_reason="insufficient_evidence",
        citations=[],
        retrieved_chunks=[],
        retrieved_chunk_ids=[],
        model_key="echo",
        prompt_template_version="v1",
    )


def _config(dataset_path: Path, experiment_id: str | None = None) -> ExperimentConfig:
    return ExperimentConfig(
        experiment_id=experiment_id or str(uuid.uuid4()),
        name="smoke",
        organization_id=uuid.uuid4(),
        workspace_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        knowledge_base_id=uuid.UUID(KB_ID),
        dataset_id="kb-hr-fa-smoke",
        dataset_version="1.0.0",
        dataset_path=str(dataset_path),
        top_k=8,
        thresholds=ExperimentThresholds(
            recall_at_k=0.70,
            mrr=0.50,
            groundedness=0.70,
            citation_precision_mean=0.70,
            abstention_precision=0.80,
        ),
    )


# --- Dataset validation ---


def test_load_valid_dataset(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path / "ds", questions=[_answerable(), _abstain()])
    dataset = load_dataset(dataset_dir)
    assert dataset.manifest.dataset_id == "kb-hr-fa-smoke"
    assert len(dataset.questions) == 2


def test_reject_malformed_jsonl(tmp_path: Path) -> None:
    dataset_dir = tmp_path / "bad"
    dataset_dir.mkdir()
    (dataset_dir / "manifest.json").write_text(
        json.dumps(
            {
                "dataset_id": "kb-hr-fa-smoke",
                "dataset_version": "1.0.0",
                "knowledge_base_id": KB_ID,
                "question_count": 1,
            }
        ),
        encoding="utf-8",
    )
    (dataset_dir / "dataset.jsonl").write_text("{not-json\n", encoding="utf-8")
    with pytest.raises(DatasetValidationError) as exc:
        load_dataset(dataset_dir)
    assert exc.value.details.get("line") == 1


def test_reject_missing_difficulty(tmp_path: Path) -> None:
    row = _answerable()
    del row["difficulty"]
    dataset_dir = _write_dataset(tmp_path / "ds", questions=[row], question_count=1)
    with pytest.raises(DatasetValidationError) as exc:
        load_dataset(dataset_dir)
    assert exc.value.details.get("line") == 1


def test_reject_missing_tags(tmp_path: Path) -> None:
    row = _answerable()
    row["tags"] = []
    dataset_dir = _write_dataset(tmp_path / "ds", questions=[row])
    with pytest.raises(DatasetValidationError):
        load_dataset(dataset_dir)


# --- Metrics ---


def test_recall_at_k_and_mrr() -> None:
    outcomes = [
        QuestionOutcome(
            question_id="q1",
            status="ok",
            expected_chunk_ids=[CHUNK_A],
            retrieved_chunk_ids=[CHUNK_B, CHUNK_A],
        ),
        QuestionOutcome(
            question_id="q2",
            status="ok",
            expected_chunk_ids=[CHUNK_A],
            retrieved_chunk_ids=[CHUNK_B],
        ),
    ]
    recall, n = recall_at_k(outcomes)
    mrr, _ = mean_reciprocal_rank(outcomes)
    assert n == 2
    assert recall == 0.5
    assert mrr == pytest.approx(0.25)  # 1/2 + 0 / 2


def test_citation_accuracy_and_precision() -> None:
    assert citation_precision([CHUNK_A], [CHUNK_A]) == 1.0
    assert is_citation_accurate([CHUNK_A], [CHUNK_A]) is True
    assert is_citation_accurate([CHUNK_A, CHUNK_B], [CHUNK_A]) is False


def test_abstention_precision_ac08() -> None:
    outcomes = [
        QuestionOutcome(
            question_id=f"a{i}",
            status="ok",
            expect_abstention=True,
            generation_status="abstained",
            abstained=True,
        )
        for i in range(5)
    ] + [
        QuestionOutcome(
            question_id="wrong",
            status="ok",
            expect_abstention=False,
            generation_status="abstained",
            abstained=True,
            expected_chunk_ids=[CHUNK_A],
        )
    ]
    prec, _ = abstention_precision(outcomes)
    rec, _ = abstention_recall(outcomes)
    assert prec == pytest.approx(5 / 6)
    assert rec == pytest.approx(1.0)


def test_thresholds_fail_groundedness() -> None:
    outcomes = [
        QuestionOutcome(
            question_id="q1",
            status="ok",
            expected_chunk_ids=[CHUNK_A],
            retrieved_chunk_ids=[CHUNK_A],
            cited_chunk_ids=[CHUNK_A],
            generation_status="completed",
        ),
        QuestionOutcome(
            question_id="q2",
            status="ok",
            expected_chunk_ids=[CHUNK_A],
            retrieved_chunk_ids=[CHUNK_A],
            cited_chunk_ids=[],
            generation_status="completed",
        ),
    ]
    report = aggregate_metrics(
        outcomes=outcomes,
        dataset_id="ds",
        dataset_version="1.0.0",
        experiment_id="exp",
        top_k=8,
    )
    # One grounded of two answerable → 0.5
    assert report.retrieval.recall_at_k == 1.0
    assert report.generation.groundedness == 0.5
    failing = evaluate_thresholds(
        report,
        recall_at_k=0.70,
        groundedness=0.70,
    )
    assert failing == ["groundedness"]


# --- Runner + persistence ---


@pytest.mark.asyncio
async def test_runner_persists_artifacts(tmp_path: Path) -> None:
    en_row = _answerable("q-en", language="en")
    en_row["question"] = "How many annual leave days?"
    dataset_dir = _write_dataset(
        tmp_path / "dataset",
        questions=[_answerable("q-fa", language="fa"), en_row, _abstain()],
    )
    storage_root = tmp_path / "artifacts"
    generation = FakeGeneration(
        results={
            "مرخصی سالانه چند روز است؟": _completed(CHUNK_A),
            str(en_row["question"]): _completed(CHUNK_A),
            "قیمت سهام شرکت چقدر است؟": _abstained(),
        }
    )
    retrieval = FakeRetrieval(
        default_chunks=[_chunk(CHUNK_A, score=0.95), _chunk(CHUNK_B, score=0.5)]
    )
    service = EvaluationService(
        retrieval_service=retrieval,
        generation_service=generation,
        storage_root=storage_root,
    )
    config = _config(dataset_dir)
    summary = await service.run(config)

    assert summary.status == EvaluationStatus.PASSED
    exp_dir = Path(summary.artifact_dir)
    assert (exp_dir / "config.json").is_file()
    assert (exp_dir / "results.jsonl").is_file()
    assert (exp_dir / "metrics.json").is_file()
    assert (exp_dir / "summary.json").is_file()

    storage = ExperimentStorage(storage_root)
    metrics = storage.read_metrics(config.experiment_id)
    assert metrics["metrics"]["retrieval"]["k"] == 8
    assert "recall_at_k" in metrics["metrics"]["retrieval"]
    assert "citation_precision_mean" in metrics["metrics"]["generation"]
    assert "by_language" in metrics
    assert set(metrics["by_language"].keys()) >= {"fa", "en"}

    results = storage.read_results(config.experiment_id)
    assert len(results) == 3
    assert all(r.e2e_latency_ms is not None for r in results if r.status == "ok")
    assert all(r.prompt_tokens is None for r in results)


@pytest.mark.asyncio
async def test_runner_fails_thresholds(tmp_path: Path) -> None:
    wrong_chunk = "018f0000-0000-7000-8000-000000000099"
    dataset_dir = _write_dataset(tmp_path / "dataset", questions=[_answerable()])
    retrieval = FakeRetrieval(default_chunks=[_chunk(wrong_chunk)])
    generation = FakeGeneration(
        default=GenerationResult(
            status=GenerationStatus.COMPLETED,
            answer="guess [1]",
            citations=[_citation(wrong_chunk)],
            retrieved_chunks=[_chunk(wrong_chunk)],
            retrieved_chunk_ids=[uuid.UUID(wrong_chunk)],
        )
    )
    service = EvaluationService(
        retrieval_service=retrieval,
        generation_service=generation,
        storage_root=tmp_path / "out",
    )
    config = _config(dataset_dir)
    summary = await service.run(config)
    assert summary.status == EvaluationStatus.FAILED
    assert "recall_at_k" in summary.failing_metrics or "groundedness" in summary.failing_metrics


@pytest.mark.asyncio
async def test_reproducible_metrics_distinct_ids(tmp_path: Path) -> None:
    dataset_dir = _write_dataset(tmp_path / "dataset", questions=[_answerable(), _abstain()])
    retrieval = FakeRetrieval(default_chunks=[_chunk(CHUNK_A)])
    q = "مرخصی سالانه چند روز است؟"
    generation = FakeGeneration(
        results={
            q: _completed(CHUNK_A),
            "قیمت سهام شرکت چقدر است؟": _abstained(),
        }
    )
    service = EvaluationService(
        retrieval_service=retrieval,
        generation_service=generation,
        storage_root=tmp_path / "out",
    )
    s1 = await service.run(_config(dataset_dir, experiment_id="run-1"))
    s2 = await service.run(_config(dataset_dir, experiment_id="run-2"))
    assert s1.experiment_id != s2.experiment_id
    assert s1.metrics.retrieval.recall_at_k == s2.metrics.retrieval.recall_at_k
    assert s1.metrics.generation.groundedness == s2.metrics.generation.groundedness


def test_citation_ref_model() -> None:
    ref = CitationRef(chunk_id=CHUNK_A, document_id=DOC_A)
    assert ref.chunk_id == CHUNK_A
    assert Difficulty.EASY.value == "easy"
    assert QuestionLanguage.FA.value == "fa"
