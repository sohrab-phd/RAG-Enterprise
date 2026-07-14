"""Chat API tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import pytest
from httpx import ASGITransport, AsyncClient

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.dependencies.providers import AppContainer, set_container
from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from rag_enterprise.generation import persistence as generation_models  # noqa: F401
from rag_enterprise.generation.prompt_builder import PromptBuilder
from rag_enterprise.generation.providers import OpenAICompatibleLLMProvider
from rag_enterprise.generation.service import GenerationService
from rag_enterprise.indexing import models as indexing_models  # noqa: F401
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.knowledge import models as knowledge_models  # noqa: F401
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.infrastructure.storage import InMemoryFileStorage
from rag_enterprise.knowledge.models import KnowledgeBase
from rag_enterprise.knowledge.registration import register_knowledge_handlers
from rag_enterprise.main import create_app
from rag_enterprise.retrieval.models import RetrievedChunk, SearchResponse


@dataclass
class FakeRetrieval:
    response: SearchResponse

    async def retrieve(self, request: object) -> SearchResponse:
        return self.response


@pytest.fixture
async def chat_client() -> AsyncClient:
    settings = DatabaseSettings(url="sqlite+aiosqlite:///:memory:", echo=False)
    engine, session_factory = create_engine_and_session_factory(settings)
    assert session_factory is not None
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)

    org_id = uuid.UUID("018f0000-0000-7000-8000-000000000021")
    workspace_id = uuid.UUID("018f0000-0000-7000-8000-000000000022")
    user_id = uuid.UUID("018f0000-0000-7000-8000-000000000023")

    async with session_factory() as session:
        kb = KnowledgeBase(
            organization_id=org_id,
            workspace_id=workspace_id,
            name="Chat KB",
            status=KnowledgeBaseStatus.ACTIVE,
        )
        session.add(kb)
        await session.commit()
        await session.refresh(kb)
        kb_id = kb.id

    chunk = RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=kb_id,
        score=0.95,
        text="مرخصی سالانه ۲۰ روز کاری است.",
        chunk_index=0,
        start_char=0,
        end_char=30,
        language="fa",
    )
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="مرخصی",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )

    container = AppContainer(settings=get_settings())
    container.engine = engine
    container.session_factory = session_factory
    container.file_storage = InMemoryFileStorage()
    container.embedding_provider = BgeM3EmbeddingProvider(mode="deterministic")
    container.llm_provider = OpenAICompatibleLLMProvider(mode="echo")
    container.retrieval_service = retrieval  # type: ignore[assignment]
    container.indexing_service = None
    container.generation_service = GenerationService(
        session_factory=session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=container.llm_provider,
        prompt_builder=PromptBuilder(),
        min_evidence_score=0.25,
        retry_delays_seconds=(0.0,),
    )
    register_knowledge_handlers(
        command_dispatcher=container.command_dispatcher,
        query_dispatcher=container.query_dispatcher,
        session_factory=session_factory,
        file_storage=container.file_storage,
    )
    set_container(container)

    app = create_app()
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        headers={
            "X-Organization-Id": str(org_id),
            "X-User-Id": str(user_id),
        },
    ) as client:
        client.workspace_id = workspace_id  # type: ignore[attr-defined]
        client.kb_id = kb_id  # type: ignore[attr-defined]
        yield client

    import rag_enterprise.core.dependencies.providers as providers

    providers._container = None
    await engine.dispose()


@pytest.mark.asyncio
async def test_chat_endpoint(chat_client: AsyncClient) -> None:
    workspace_id = chat_client.workspace_id  # type: ignore[attr-defined]
    kb_id = chat_client.kb_id  # type: ignore[attr-defined]
    response = await chat_client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        json={
            "question": "سیاست مرخصی چیست؟",
            "knowledge_base_id": str(kb_id),
            "top_k": 5,
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["abstained"] is False
    assert data["answer"]
    assert data["citations"]
    assert data["retrieved_chunks"]
    assert data["conversation_id"]


@pytest.mark.asyncio
async def test_chat_follow_up(chat_client: AsyncClient) -> None:
    workspace_id = chat_client.workspace_id  # type: ignore[attr-defined]
    kb_id = chat_client.kb_id  # type: ignore[attr-defined]
    first = await chat_client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        json={"question": "Leave policy?", "knowledge_base_id": str(kb_id)},
    )
    conversation_id = first.json()["data"]["conversation_id"]
    second = await chat_client.post(
        f"/api/v1/workspaces/{workspace_id}/chat",
        json={
            "question": "How many days?",
            "knowledge_base_id": str(kb_id),
            "conversation_id": conversation_id,
        },
    )
    assert second.status_code == 200
    assert second.json()["data"]["conversation_id"] == conversation_id
