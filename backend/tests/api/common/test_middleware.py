"""Request context middleware tests."""

import pytest
from httpx import AsyncClient

from rag_enterprise.api.common.context import CORRELATION_ID_HEADER, REQUEST_ID_HEADER


@pytest.mark.asyncio
async def test_request_id_is_generated_when_missing(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert REQUEST_ID_HEADER in response.headers
    assert response.headers[REQUEST_ID_HEADER]


@pytest.mark.asyncio
async def test_correlation_id_defaults_to_request_id(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert CORRELATION_ID_HEADER in response.headers
    assert response.headers[CORRELATION_ID_HEADER] == response.headers[REQUEST_ID_HEADER]


@pytest.mark.asyncio
async def test_correlation_id_is_propagated_from_request_header(client: AsyncClient) -> None:
    correlation_id = "corr-12345"
    response = await client.get(
        "/api/v1/health",
        headers={CORRELATION_ID_HEADER: correlation_id},
    )

    assert response.status_code == 200
    assert response.headers[CORRELATION_ID_HEADER] == correlation_id


@pytest.mark.asyncio
async def test_request_id_is_propagated_from_request_header(client: AsyncClient) -> None:
    request_id = "req-abcde"
    response = await client.get(
        "/api/v1/health",
        headers={REQUEST_ID_HEADER: request_id},
    )

    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == request_id
