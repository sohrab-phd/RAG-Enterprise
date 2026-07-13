"""API versioning helper tests."""

from rag_enterprise.api.common.versioning import (
    CURRENT_API_VERSION,
    build_versioned_path,
    get_api_version_from_path,
    is_supported_api_version,
)


def test_build_versioned_path() -> None:
    assert build_versioned_path("v1", "/health") == "/api/v1/health"


def test_get_api_version_from_path() -> None:
    assert get_api_version_from_path("/api/v1/health") == "v1"
    assert get_api_version_from_path("/health") is None


def test_supported_api_versions() -> None:
    assert is_supported_api_version(CURRENT_API_VERSION) is True
    assert is_supported_api_version("v99") is False
