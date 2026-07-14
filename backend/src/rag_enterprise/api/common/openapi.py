"""OpenAPI customization for the API foundation."""

from __future__ import annotations

from typing import Any

from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from rag_enterprise.api.common.errors import ErrorDetail, ErrorEnvelope
from rag_enterprise.api.common.versioning import get_openapi_version
from rag_enterprise.core.config.settings import Settings

OPENAPI_TAGS: list[dict[str, str]] = [
    {
        "name": "health",
        "description": (
            "Operational probes: /live (liveness), /ready (readiness dependencies), "
            "/system (inventory counts), and legacy /health."
        ),
    },
    {
        "name": "knowledge-bases",
        "description": "Knowledge base administration.",
    },
    {
        "name": "folders",
        "description": "Folder hierarchy operations.",
    },
    {
        "name": "documents",
        "description": "Document lifecycle and metadata.",
    },
    {
        "name": "uploads",
        "description": "Upload session management.",
    },
    {
        "name": "document-versions",
        "description": "Document version history.",
    },
    {
        "name": "retrieval",
        "description": "Dense vector retrieval over indexed knowledge bases.",
    },
    {
        "name": "chat",
        "description": "Grounded RAG chat with citations and abstention.",
    },
]


def configure_openapi(app: FastAPI, settings: Settings) -> None:
    """Attach a customized OpenAPI schema generator to the application."""

    def custom_openapi() -> dict[str, Any]:
        if app.openapi_schema:
            return app.openapi_schema

        schema = get_openapi(
            title=settings.app_name,
            version=get_openapi_version(),
            description=(
                "Production-grade RAG platform API. "
                "Successful responses use `{success: true, data: ...}` and "
                "errors use `{success: false, error: {code, message, details}}`."
            ),
            routes=app.routes,
            tags=OPENAPI_TAGS,
        )
        schema.setdefault("components", {}).setdefault("schemas", {})
        schema["components"]["schemas"]["ErrorDetail"] = ErrorDetail.model_json_schema()
        schema["components"]["schemas"]["ErrorEnvelope"] = ErrorEnvelope.model_json_schema()
        app.openapi_schema = schema
        return schema

    app.openapi = custom_openapi  # type: ignore[method-assign]
