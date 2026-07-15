"""RC1.3 — single end-to-end RAG happy path (Persian leave-policy golden path)."""

from __future__ import annotations

import json
import re
import uuid
from collections.abc import AsyncIterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine

from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import get_container
from rag_enterprise.db.base import ModelBase
from rag_enterprise.evaluation.metrics import is_citation_accurate, is_grounded
from rag_enterprise.evaluation.models import ExperimentThresholds
from rag_enterprise.main import create_app

FIXTURES = Path(__file__).resolve().parent / "fixtures"
GOLDEN = json.loads((FIXTURES / "golden_path.json").read_text(encoding="utf-8"))
SAMPLE_DOCUMENT = (FIXTURES / GOLDEN["document_file"]).read_text(encoding="utf-8").encode("utf-8")

ORG_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000e1")
WORKSPACE_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000e2")
USER_ID = uuid.UUID("018f0000-0000-7000-8000-0000000000e3")


@pytest.fixture
async def e2e_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    """Boot the full application lifespan with deterministic local providers."""
    eval_root = tmp_path / "eval-artifacts"
    upload_root = tmp_path / "storage" / "uploads"
    monkeypatch.setenv("EVALUATION_STORAGE_ROOT", str(eval_root))
    monkeypatch.setenv("FILE_STORAGE_ROOT", str(upload_root))
    monkeypatch.setenv("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
    monkeypatch.setenv("LLM_BACKEND", "mock")
    monkeypatch.setenv("EMBEDDING_BACKEND", "deterministic")
    # Deterministic embeddings are not semantic; disable score gate for local e2e.
    monkeypatch.setenv("GENERATION_MIN_EVIDENCE_SCORE", "0.0")
    monkeypatch.setenv("APP_ENV", "test")
    get_settings.cache_clear()

    app = create_app()
    async with app.router.lifespan_context(app):
        container = get_container()
        assert container.engine is not None
        await _create_schema(container.engine)

        transport = ASGITransport(app=app, raise_app_exceptions=False)
        async with AsyncClient(
            transport=transport,
            base_url="http://test",
            headers={
                "X-Organization-Id": str(ORG_ID),
                "X-User-Id": str(USER_ID),
            },
        ) as client:
            yield client

    get_settings.cache_clear()


async def _create_schema(engine: AsyncEngine) -> None:
    import rag_enterprise.generation.persistence  # noqa: F401
    import rag_enterprise.indexing.models  # noqa: F401
    import rag_enterprise.knowledge.models  # noqa: F401

    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)


def _data(response: object) -> dict[str, object]:
    body = response.json()  # type: ignore[attr-defined]
    assert body["success"] is True
    data = body["data"]
    assert isinstance(data, dict)
    return data


@pytest.mark.asyncio
async def test_rag_happy_path_persian_leave_policy(e2e_client: AsyncClient) -> None:
    """One golden path: KB → upload Persian policy → process/index → retrieve → chat → cite."""
    base = f"/api/v1/workspaces/{WORKSPACE_ID}"
    container = get_container()
    assert container.session_factory is not None
    assert container.file_storage is not None
    from rag_enterprise.knowledge.infrastructure.filesystem import FileSystemStorage

    assert isinstance(container.file_storage, FileSystemStorage)
    assert container.indexing_service is not None
    assert container.evaluation_service is not None

    # --- Start: create + publish knowledge base (draft → active) ---
    created = await e2e_client.post(
        f"{base}/knowledge-bases",
        json={
            "name": "RC1.3 HR Policy KB",
            "default_language": "fa",
            "description": GOLDEN["document_title"],
        },
    )
    assert created.status_code == 201
    kb_id = str(_data(created)["id"])

    published = await e2e_client.post(f"{base}/knowledge-bases/{kb_id}/publish")
    assert published.status_code == 200
    assert _data(published)["status"] == "active"

    # --- Upload Persian sample document ---
    document = await e2e_client.post(
        f"{base}/knowledge-bases/{kb_id}/documents",
        json={
            "title": GOLDEN["document_title"],
            "declared_language": "fa",
        },
    )
    assert document.status_code == 201
    document_id = str(_data(document)["id"])

    upload = await e2e_client.post(
        f"{base}/knowledge-bases/{kb_id}/uploads",
        json={
            "file_name": GOLDEN["document_file"],
            "file_size_bytes": len(SAMPLE_DOCUMENT),
            "mime_type": "text/plain",
            "document_id": document_id,
        },
    )
    assert upload.status_code == 201
    upload_id = str(_data(upload)["id"])

    complete = await e2e_client.post(
        f"{base}/knowledge-bases/{kb_id}/uploads/{upload_id}/complete",
        content=SAMPLE_DOCUMENT,
    )
    assert complete.status_code == 200

    version = await e2e_client.post(
        f"{base}/knowledge-bases/{kb_id}/documents/{document_id}/versions",
        json={"upload_id": upload_id},
    )
    assert version.status_code == 201
    version_payload = _data(version)
    assert version_payload["processing_status"] == "uploaded"

    # --- Synchronous process & index (operator API) ---
    process = await e2e_client.post(f"{base}/documents/{document_id}/process")
    assert process.status_code == 200
    process_data = _data(process)
    assert process_data["current_status"] == "indexed"
    assert int(process_data["processed_chunks"]) >= 1
    assert int(process_data["indexed_embeddings"]) >= 1

    # --- Ask Persian question: retrieve evidence ---
    retrieve = await e2e_client.post(
        f"{base}/retrieve",
        json={
            "query": GOLDEN["question"],
            "knowledge_base_id": kb_id,
            "top_k": 5,
            "language": "fa",
        },
    )
    assert retrieve.status_code == 200
    retrieve_data = _data(retrieve)
    assert int(retrieve_data["result_count"]) >= 1
    results = retrieve_data["results"]
    assert isinstance(results, list)
    assert any(GOLDEN["source_must_contain"] in str(item["text"]) for item in results)
    chunk_id = uuid.UUID(str(results[0]["chunk_id"]))

    # --- Generate grounded answer ---
    chat = await e2e_client.post(
        f"{base}/chat",
        json={
            "question": GOLDEN["question"],
            "knowledge_base_id": kb_id,
            "language_hint": "fa",
            "top_k": 5,
        },
    )
    assert chat.status_code == 200
    chat_data = _data(chat)

    assert chat_data["abstained"] is False
    assert chat_data["status"] == "completed"
    assert chat_data["answer"]
    assert re.search(GOLDEN["answer_pattern_echo"], str(chat_data["answer"])) is not None

    citations = chat_data["citations"]
    retrieved_chunks = chat_data["retrieved_chunks"]
    assert isinstance(citations, list) and len(citations) >= 1
    assert isinstance(retrieved_chunks, list) and len(retrieved_chunks) >= 1

    retrieved_ids = {str(item["chunk_id"]) for item in retrieved_chunks}
    cited_ids = [str(item["chunk_id"]) for item in citations]
    assert all(cid in retrieved_ids for cid in cited_ids)
    assert str(chunk_id) in retrieved_ids
    assert str(chunk_id) in cited_ids

    assert is_grounded(
        generation_status=str(chat_data["status"]),
        cited_chunk_ids=cited_ids,
        expected_chunk_ids=[str(chunk_id)],
        retrieved_chunk_ids=list(retrieved_ids),
    )
    assert is_citation_accurate(cited_ids, [str(chunk_id)]) is True

    # --- Evaluation engine verification (same question, real retrieve + generate) ---
    dataset_dir = Path(get_settings().evaluation_storage_root) / "datasets" / "rc1-3-golden"
    dataset_dir.mkdir(parents=True, exist_ok=True)
    manifest = {
        "dataset_id": GOLDEN["dataset_id"],
        "dataset_version": GOLDEN["dataset_version"],
        "knowledge_base_id": kb_id,
        "question_count": 1,
        "languages": ["fa"],
        "created_at": "2026-07-14T00:00:00Z",
        "notes": "RC1.3 happy-path golden question",
    }
    question_row = {
        "id": "rc1-3-leave-days",
        "question": GOLDEN["question"],
        "expected_answer": GOLDEN["expected_answer_fa"],
        "expected_citations": [
            {"chunk_id": str(chunk_id), "document_id": document_id},
        ],
        "knowledge_base_id": kb_id,
        "difficulty": "easy",
        "language": "fa",
        "tags": ["leave", "hr", "rc1.3"],
        "expect_abstention": False,
    }
    (dataset_dir / "manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False),
        encoding="utf-8",
    )
    (dataset_dir / "dataset.jsonl").write_text(
        json.dumps(question_row, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    config = container.evaluation_service.create_config(
        name="rc1.3-happy-path",
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        knowledge_base_id=uuid.UUID(kb_id),
        dataset_id=GOLDEN["dataset_id"],
        dataset_version=GOLDEN["dataset_version"],
        dataset_path=str(dataset_dir),
        top_k=5,
        llm="echo",
        min_evidence_score=0.0,
        thresholds=ExperimentThresholds(
            recall_at_k=1.0,
            mrr=1.0,
            groundedness=1.0,
            citation_precision_mean=1.0,
            abstention_precision=None,
        ),
    )
    summary = await container.evaluation_service.run(config)
    assert summary.error_count == 0
    assert summary.failing_metrics == []
