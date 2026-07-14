"""FastAPI application lifespan management."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.core.config.validation import (
    ConfigurationError,
    emit_configuration_report,
    validate_configuration,
)
from rag_enterprise.core.dependencies.providers import lifespan_container
from rag_enterprise.core.logging.setup import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage application startup and shutdown lifecycle."""
    settings = get_settings()

    try:
        validate_configuration(settings)
    except ConfigurationError as exc:
        # Fail fast before DI / request handling. Emit a plain console report
        # so operators see grouped errors even if structured logging is quiet.
        emit_configuration_report(str(exc))
        raise SystemExit(1) from exc

    configure_logging(
        log_level=settings.log_level,
        json_logs=settings.is_production,
    )

    logger.info(
        "configuration_validated",
        app_name=settings.app_name,
        environment=settings.app_env,
        llm_backend=settings.llm_backend,
        embedding_backend=settings.embedding_backend,
        evaluation_storage_root=settings.evaluation_storage_root,
    )

    logger.info(
        "application_starting",
        app_name=settings.app_name,
        environment=settings.app_env,
    )

    async with lifespan_container(settings):
        logger.info("application_ready")
        yield

    logger.info("application_shutdown_complete")
