"""Success and error envelope model tests."""

from rag_enterprise.api.common.errors import ErrorEnvelope, error_response
from rag_enterprise.api.common.pagination import paginated_response
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.application.dto.base import PaginationDTO


def test_success_envelope_shape() -> None:
    envelope = success_response({"id": "123"})

    assert isinstance(envelope, SuccessEnvelope)
    assert envelope.success is True
    assert envelope.data == {"id": "123"}


def test_error_envelope_shape() -> None:
    envelope = error_response(
        code="not_found",
        message="Resource not found",
        details={"resource": "document"},
    )

    assert isinstance(envelope, ErrorEnvelope)
    assert envelope.success is False
    assert envelope.error.code == "not_found"
    assert envelope.error.message == "Resource not found"
    assert envelope.error.details == {"resource": "document"}


def test_paginated_envelope_shape() -> None:
    page = PaginationDTO[str](
        items=["a", "b"],
        page=1,
        page_size=10,
        total_items=2,
    )
    envelope = paginated_response(page)

    assert envelope.success is True
    assert envelope.data.items == ["a", "b"]
    assert envelope.data.pagination.page == 1
    assert envelope.data.pagination.total_pages == 1
    assert envelope.data.pagination.has_next is False
    assert envelope.data.pagination.has_previous is False
