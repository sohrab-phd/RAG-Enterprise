"""Exception handler tests."""

import pytest
from fastapi import FastAPI, Query
from httpx import ASGITransport, AsyncClient

from rag_enterprise.api.common.errors import ApplicationException, UnexpectedError
from rag_enterprise.api.common.handlers import register_exception_handlers
from rag_enterprise.api.common.middleware import RequestContextMiddleware
from rag_enterprise.application.common.errors import ApplicationError, ErrorCode


@pytest.fixture
def handler_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    register_exception_handlers(app)

    @app.get("/validation")
    async def validation_endpoint(value: int = Query(..., ge=1)) -> dict[str, int]:
        return {"value": value}

    @app.get("/application")
    async def application_endpoint() -> None:
        raise ApplicationException(
            ApplicationError(code=ErrorCode.NOT_FOUND, message="Item not found"),
        )

    @app.get("/unexpected")
    async def unexpected_endpoint() -> None:
        raise UnexpectedError("Provider unavailable", details={"provider": "search"})

    @app.get("/uncaught")
    async def uncaught_endpoint() -> None:
        raise RuntimeError("boom")

    return app


@pytest.fixture
async def handler_client(handler_app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=handler_app, raise_app_exceptions=False)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest.mark.asyncio
async def test_validation_error_uses_standard_envelope(handler_client: AsyncClient) -> None:
    response = await handler_client.get("/validation", params={"value": 0})

    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == ErrorCode.VALIDATION_FAILED
    assert body["error"]["message"] == "Request validation failed"
    assert "errors" in body["error"]["details"]


@pytest.mark.asyncio
async def test_application_error_uses_standard_envelope(handler_client: AsyncClient) -> None:
    response = await handler_client.get("/application")

    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == ErrorCode.NOT_FOUND
    assert body["error"]["message"] == "Item not found"


@pytest.mark.asyncio
async def test_unexpected_error_uses_standard_envelope(handler_client: AsyncClient) -> None:
    response = await handler_client.get("/unexpected")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == ErrorCode.INTERNAL_ERROR
    assert body["error"]["message"] == "Provider unavailable"
    assert body["error"]["details"] == {"provider": "search"}


@pytest.mark.asyncio
async def test_uncaught_exception_uses_safe_internal_error(handler_client: AsyncClient) -> None:
    response = await handler_client.get("/uncaught")

    assert response.status_code == 500
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == ErrorCode.INTERNAL_ERROR
    assert body["error"]["message"] == "An unexpected error occurred"
