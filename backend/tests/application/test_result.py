"""Result type tests."""

import pytest

from rag_enterprise.application.common import ApplicationError, Result


def test_ok_result_is_successful() -> None:
    result = Result.ok("value")

    assert result.is_success
    assert not result.is_failure
    assert result.unwrap() == "value"


def test_ok_none_result_unwraps_to_none() -> None:
    result = Result.ok(None)
    assert result.is_success
    assert result.unwrap() is None


def test_fail_result_is_failure() -> None:
    error = ApplicationError(code="test_error", message="failed")
    result = Result.fail(error)

    assert result.is_failure
    assert result.error == error


def test_unwrap_failed_result_raises() -> None:
    result = Result.fail(ApplicationError(code="test_error", message="failed"))

    with pytest.raises(ValueError, match="Cannot unwrap a failed result"):
        result.unwrap()


def test_map_applies_function_on_success() -> None:
    result = Result.ok(2).map(lambda value: value + 1)

    assert result.is_success
    assert result.unwrap() == 3


def test_map_preserves_failure() -> None:
    error = ApplicationError(code="test_error", message="failed")
    result = Result[int].fail(error).map(lambda value: value + 1)

    assert result.is_failure
    assert result.error == error
