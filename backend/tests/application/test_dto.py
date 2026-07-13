"""DTO validation tests."""

import pytest
from pydantic import ValidationError

from rag_enterprise.application.dto import PaginationDTO, RequestDTO, ResponseDTO


class SampleRequest(RequestDTO):
    name: str


class SampleResponse(ResponseDTO):
    name: str


def test_request_dto_strips_whitespace() -> None:
    request = SampleRequest(name="  hello  ")
    assert request.name == "hello"


def test_request_dto_rejects_unknown_fields() -> None:
    with pytest.raises(ValidationError):
        SampleRequest(name="hello", extra="value")  # type: ignore[call-arg]


def test_pagination_dto_computes_totals() -> None:
    page = PaginationDTO[SampleResponse](
        items=[SampleResponse(name="a"), SampleResponse(name="b")],
        page=1,
        page_size=10,
        total_items=2,
    )

    assert page.total_pages == 1
    assert not page.has_next


def test_pagination_dto_rejects_items_longer_than_page_size() -> None:
    with pytest.raises(ValidationError, match="items length cannot exceed page_size"):
        PaginationDTO[SampleResponse](
            items=[SampleResponse(name="a"), SampleResponse(name="b")],
            page=1,
            page_size=1,
            total_items=2,
        )
