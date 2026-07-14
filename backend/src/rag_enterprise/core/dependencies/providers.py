"""Application container and FastAPI Depends providers.

This module establishes the DI pattern for application-wide dependencies.
"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from rag_enterprise.application.commands.dispatcher import CommandDispatcher
from rag_enterprise.application.interfaces.embedding import EmbeddingProvider
from rag_enterprise.application.interfaces.file_storage import FileStorage
from rag_enterprise.application.interfaces.llm import LLMProvider
from rag_enterprise.application.queries.dispatcher import QueryDispatcher
from rag_enterprise.core.config.settings import Settings, get_settings
from rag_enterprise.db.session.factory import create_engine_and_session_factory
from rag_enterprise.evaluation.service import EvaluationService
from rag_enterprise.generation.prompt_builder import PromptBuilder, PromptBuilderConfig
from rag_enterprise.generation.providers import OpenAICompatibleLLMProvider
from rag_enterprise.generation.service import GenerationService
from rag_enterprise.indexing.providers import BgeM3EmbeddingProvider
from rag_enterprise.indexing.service import IndexingService
from rag_enterprise.knowledge.infrastructure.filesystem import FileSystemStorage
from rag_enterprise.knowledge.registration import register_knowledge_handlers
from rag_enterprise.retrieval.service import RetrievalService


@dataclass
class AppContainer:
    """Lightweight service container for application-wide dependencies."""

    settings: Settings
    engine: AsyncEngine | None = None
    session_factory: async_sessionmaker[AsyncSession] | None = None
    file_storage: FileStorage | None = None
    embedding_provider: EmbeddingProvider | None = None
    llm_provider: LLMProvider | None = None
    indexing_service: IndexingService | None = None
    retrieval_service: RetrievalService | None = None
    generation_service: GenerationService | None = None
    evaluation_service: EvaluationService | None = None
    command_dispatcher: CommandDispatcher = field(default_factory=CommandDispatcher)
    query_dispatcher: QueryDispatcher = field(default_factory=QueryDispatcher)
    _initialized: bool = field(default=False, repr=False)

    @property
    def is_initialized(self) -> bool:
        return self._initialized

    async def initialize(self) -> None:
        """Initialize external resources during application startup."""
        if self._initialized:
            return

        self.engine, self.session_factory = create_engine_and_session_factory(
            self.settings.database
        )
        self.file_storage = FileSystemStorage(self.settings.file_storage_root)
        self.embedding_provider = BgeM3EmbeddingProvider(
            mode=self.settings.embedding_backend,
            model_key=self.settings.embedding_model_key,
            dimensions=self.settings.embedding_dimensions,
        )
        self.llm_provider = OpenAICompatibleLLMProvider(
            mode=self.settings.llm_backend,
            model_key=self.settings.llm_model_key,
            base_url=self.settings.llm_base_url,
            api_key=self.settings.llm_api_key,
            timeout_seconds=self.settings.llm_timeout_seconds,
        )
        if self.session_factory is not None:
            register_knowledge_handlers(
                command_dispatcher=self.command_dispatcher,
                query_dispatcher=self.query_dispatcher,
                session_factory=self.session_factory,
                file_storage=self.file_storage,
            )
            self.indexing_service = IndexingService(
                session_factory=self.session_factory,
                embedding_provider=self.embedding_provider,
                batch_size=self.settings.embedding_batch_size,
                retry_delays_seconds=(0.0, 0.0, 0.0),
            )
            self.retrieval_service = RetrievalService(
                session_factory=self.session_factory,
                embedding_provider=self.embedding_provider,
            )
            self.generation_service = GenerationService(
                session_factory=self.session_factory,
                retrieval_service=self.retrieval_service,
                llm_provider=self.llm_provider,
                prompt_builder=PromptBuilder(
                    PromptBuilderConfig(
                        max_history_messages=self.settings.generation_max_history_messages
                    )
                ),
                min_evidence_score=self.settings.generation_min_evidence_score,
                max_history_messages=self.settings.generation_max_history_messages,
                default_top_k=self.settings.retrieval_default_top_k,
                llm_timeout_seconds=self.settings.llm_timeout_seconds,
                retry_delays_seconds=(0.0, 0.0),
            )
            self.evaluation_service = EvaluationService(
                retrieval_service=self.retrieval_service,
                generation_service=self.generation_service,
                storage_root=self.settings.evaluation_storage_root,
            )
        self._initialized = True

    async def shutdown(self) -> None:
        """Release external resources during application shutdown."""
        if not self._initialized:
            return

        if self.engine is not None:
            await self.engine.dispose()
            self.engine = None
            self.session_factory = None
            self.file_storage = None
            self.embedding_provider = None
            self.llm_provider = None
            self.indexing_service = None
            self.retrieval_service = None
            self.generation_service = None
            self.evaluation_service = None

        self._initialized = False


_container: AppContainer | None = None


def get_container() -> AppContainer:
    """Return the application container singleton."""
    if _container is None:
        raise RuntimeError("Application container has not been initialized")
    return _container


def set_container(container: AppContainer) -> None:
    """Set the application container (called during lifespan startup)."""
    global _container
    _container = container


@asynccontextmanager
async def lifespan_container(settings: Settings) -> AsyncIterator[AppContainer]:
    """Create and manage the application container lifecycle."""
    container = AppContainer(settings=settings)
    await container.initialize()
    set_container(container)
    try:
        yield container
    finally:
        await container.shutdown()
        global _container
        _container = None


def get_settings_dep() -> Settings:
    """FastAPI dependency for settings injection."""
    return get_settings()


SettingsDep = Annotated[Settings, Depends(get_settings_dep)]
