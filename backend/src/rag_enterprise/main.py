"""FastAPI application entry point."""

from fastapi import FastAPI

from rag_enterprise import __version__
from rag_enterprise.api.common.handlers import register_exception_handlers
from rag_enterprise.api.common.middleware import RequestContextMiddleware, RequestLoggingMiddleware
from rag_enterprise.api.common.openapi import configure_openapi
from rag_enterprise.api.v1 import api_v1_router
from rag_enterprise.core.config.settings import get_settings
from rag_enterprise.lifespan import lifespan


def create_app() -> FastAPI:
    """Application factory for testability and explicit configuration."""
    settings = get_settings()

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Production-grade RAG platform API",
        lifespan=lifespan,
        docs_url="/docs" if not settings.is_production else None,
        redoc_url="/redoc" if not settings.is_production else None,
    )

    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(RequestContextMiddleware)

    register_exception_handlers(app)
    configure_openapi(app, settings)

    app.include_router(api_v1_router, prefix=settings.api_v1_prefix)

    return app


app = create_app()
