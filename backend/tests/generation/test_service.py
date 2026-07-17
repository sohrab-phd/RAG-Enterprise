"""GenerationService tests with fake retrieval and LLM."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from rag_enterprise.core.config.database import DatabaseSettings
from rag_enterprise.db.base import ModelBase
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from rag_enterprise.generation import persistence as generation_models  # noqa: F401
from rag_enterprise.generation.models import (
    GenerationRequest,
    GenerationStatus,
    MessageRole,
    MessageTurn,
)
from rag_enterprise.generation.prompt_builder import PromptBuilder
from rag_enterprise.generation.providers import MockProvider
from rag_enterprise.generation.repositories import MessageRepository
from rag_enterprise.generation.service import GenerationService
from rag_enterprise.indexing import models as indexing_models  # noqa: F401
from rag_enterprise.knowledge import models as knowledge_models  # noqa: F401
from rag_enterprise.knowledge.authorization import ALL_KNOWLEDGE_PERMISSIONS
from rag_enterprise.knowledge.enums import KnowledgeBaseStatus
from rag_enterprise.knowledge.models import KnowledgeBase
from rag_enterprise.retrieval.models import RetrievedChunk, SearchResponse


@dataclass
class FakeRetrieval:
    response: SearchResponse

    async def retrieve(self, request: object) -> SearchResponse:
        return self.response


@dataclass
class SlowLLM(MockProvider):
    delay: float = 0.2

    def __init__(self, delay: float = 0.2) -> None:
        super().__init__(model_key="slow-echo")
        self.delay = delay

    async def complete(self, request: object) -> object:  # type: ignore[override]
        await asyncio.sleep(self.delay)
        return await super().complete(request)  # type: ignore[arg-type]


def _permissions() -> frozenset[str]:
    return frozenset(ALL_KNOWLEDGE_PERMISSIONS)


def _chunk(score: float = 0.9) -> RetrievedChunk:
    return RetrievedChunk(
        chunk_id=uuid.uuid4(),
        document_id=uuid.uuid4(),
        document_version_id=uuid.uuid4(),
        knowledge_base_id=uuid.uuid4(),
        score=score,
        text="Annual leave is 20 working days per year.",
        chunk_index=0,
        start_char=0,
        end_char=40,
        heading="Leave",
        language="en",
    )


@pytest.fixture
async def gen_session_factory() -> async_sessionmaker[AsyncSession]:
    settings = DatabaseSettings(url="sqlite+aiosqlite:///:memory:", echo=False)
    engine, factory = create_engine_and_session_factory(settings)
    assert factory is not None
    async with engine.begin() as connection:
        await connection.run_sync(ModelBase.metadata.create_all)
    yield factory
    await engine.dispose()


@pytest.fixture
async def seeded_kb(
    gen_session_factory: async_sessionmaker[AsyncSession],
) -> tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID]:
    org_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    user_id = uuid.uuid4()
    async with gen_session_factory() as session:
        kb = KnowledgeBase(
            organization_id=org_id,
            workspace_id=workspace_id,
            name="Gen KB",
            status=KnowledgeBaseStatus.ACTIVE,
        )
        session.add(kb)
        await session.commit()
        await session.refresh(kb)
        return org_id, workspace_id, user_id, kb.id


@pytest.mark.asyncio
async def test_grounded_answer(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk(0.9)
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="leave",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=MockProvider(),
        prompt_builder=PromptBuilder(),
        min_evidence_score=0.25,
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="How many leave days?",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
        )
    )
    assert result.status == GenerationStatus.COMPLETED
    assert result.answer
    assert result.citations
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert result.conversation_id is not None


@pytest.mark.asyncio
async def test_insufficient_evidence_abstains(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[],
            result_count=0,
            warnings=["no_results"],
        )
    )
    llm = MockProvider()
    called = {"n": 0}

    async def tracking_complete(request: object) -> object:
        called["n"] += 1
        return await MockProvider.complete(llm, request)  # type: ignore[arg-type]

    llm.complete = tracking_complete  # type: ignore[method-assign]

    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=llm,
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="Unrelated question with no evidence",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
        )
    )
    assert result.status == GenerationStatus.ABSTAINED
    assert result.abstention_reason == "insufficient_evidence"
    assert result.citations == []
    assert called["n"] == 0


@pytest.mark.asyncio
async def test_low_score_abstains(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[_chunk(0.1)],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=MockProvider(),
        min_evidence_score=0.25,
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="Anything",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
        )
    )
    assert result.status == GenerationStatus.ABSTAINED
    assert result.abstention_reason == "insufficient_evidence"


@pytest.mark.asyncio
async def test_conversation_history_window(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk()
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=MockProvider(),
        max_history_messages=5,
        retry_delays_seconds=(0.0,),
    )
    first = await service.generate(
        GenerationRequest(
            question="What is leave policy?",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
        )
    )
    second = await service.generate(
        GenerationRequest(
            question="How many days?",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
            conversation_id=first.conversation_id,
        )
    )
    assert second.conversation_id == first.conversation_id
    async with gen_session_factory() as session:
        messages = await MessageRepository(session).list_for_conversation(
            first.conversation_id  # type: ignore[arg-type]
        )
        assert len(messages) == 4  # 2 turns × user+assistant


@pytest.mark.asyncio
async def test_timeout_fails(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[_chunk()],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=SlowLLM(delay=0.3),
        llm_timeout_seconds=0.05,
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="How many leave days?",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
        )
    )
    assert result.status == GenerationStatus.FAILED
    assert result.failure_reason == "generation_timeout"


@pytest.mark.asyncio
async def test_explicit_history_used(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk()
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=MockProvider(),
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="Follow up?",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
            history=[
                MessageTurn(role=MessageRole.USER, content="First question"),
                MessageTurn(role=MessageRole.ASSISTANT, content="First answer [1]"),
            ],
        )
    )
    assert result.status == GenerationStatus.COMPLETED


@dataclass
class ScriptedLLM:
    """Deterministic LLM stub that returns a fixed completion string."""

    content: str
    model_key: str = "scripted"

    @property
    def provider_name(self) -> str:
        return "scripted"

    async def complete(self, request: object) -> object:
        from rag_enterprise.generation.providers.types import CompletionResult

        return CompletionResult(content=self.content, model_key=self.model_key)


@pytest.mark.asyncio
async def test_malformed_abstain_never_leaks_to_user(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk(0.7)
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="q",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=ScriptedLLM("ABSTAIN: insufficient_evidence[n]\n[n] chunk_id=abc text: junk"),
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="نام کاربری گلستان چیست؟",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
            language_hint="fa",
        )
    )
    assert result.status == GenerationStatus.ABSTAINED
    assert result.answer is not None
    assert "ABSTAIN" not in result.answer
    assert "chunk_id" not in result.answer
    assert "شواهد کافی" in result.answer


@pytest.mark.asyncio
async def test_citation_salvage_avoids_false_abstain(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk(0.85)
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text="leave",
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=ScriptedLLM("مرخصی سالانه ۲۰ روز کاری است."),
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question="مرخصی سالانه چند روز است؟",
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
            language_hint="fa",
        )
    )
    assert result.status == GenerationStatus.COMPLETED
    assert result.citations
    assert result.citations[0].chunk_id == chunk.chunk_id
    assert "۲۰" in (result.answer or "")
    assert "[1]" in (result.answer or "")


@pytest.mark.asyncio
async def test_question_echo_stripped_when_answer_follows(
    gen_session_factory: async_sessionmaker[AsyncSession],
    seeded_kb: tuple[uuid.UUID, uuid.UUID, uuid.UUID, uuid.UUID],
) -> None:
    org_id, workspace_id, user_id, kb_id = seeded_kb
    chunk = _chunk(0.8)
    question = "درخواست انتقالی چگونه ثبت می‌شود؟"
    retrieval = FakeRetrieval(
        SearchResponse(
            query_text=question,
            knowledge_base_id=kb_id,
            embedding_model_id=uuid.uuid4(),
            top_k=5,
            results=[chunk],
            result_count=1,
        )
    )
    service = GenerationService(
        session_factory=gen_session_factory,
        retrieval_service=retrieval,  # type: ignore[arg-type]
        llm_provider=ScriptedLLM(f"{question} فقط از طریق سامانه سجاد. [1]"),
        retry_delays_seconds=(0.0,),
    )
    result = await service.generate(
        GenerationRequest(
            question=question,
            organization_id=org_id,
            workspace_id=workspace_id,
            knowledge_base_id=kb_id,
            user_id=user_id,
            permissions=_permissions(),
            language_hint="fa",
        )
    )
    assert result.status == GenerationStatus.COMPLETED
    assert result.answer is not None
    assert not result.answer.startswith(question)
    assert "سجاد" in result.answer


def test_prompt_forbids_false_abstain_when_evidence_answers() -> None:
    """Regression: system prompt must instruct answering when evidence suffices."""
    from rag_enterprise.generation.prompt_builder import PromptBuilder

    builder = PromptBuilder()
    built = builder.build(
        question="رمز عبور اولیه گلستان چیست؟",
        chunks=[
            RetrievedChunk(
                chunk_id=uuid.uuid4(),
                document_id=uuid.uuid4(),
                document_version_id=uuid.uuid4(),
                knowledge_base_id=uuid.uuid4(),
                score=0.66,
                text="رمز عبور اولیه بهصورت پیشفرض کد ملی دانشجو است.",
                chunk_index=0,
                start_char=0,
                end_char=40,
            )
        ],
        history=[],
        language_hint="fa",
    )
    assert "Do NOT abstain when the answer is present" in built.system_prompt
    assert "Never repeat or restate the QUESTION" in built.system_prompt
    assert "Persian" in built.system_prompt
