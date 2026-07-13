"""API versioning helpers."""

from __future__ import annotations

import re

from rag_enterprise import __version__

API_VERSION_PREFIX_PATTERN = re.compile(r"^/api/v(?P<version>\d+)(?:/|$)")

CURRENT_API_VERSION = "v1"
SUPPORTED_API_VERSIONS: tuple[str, ...] = ("v1",)


def build_versioned_path(version: str, path: str) -> str:
    """Build a versioned API path from a version label and relative route path."""
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"/api/{version}{normalized_path}"


def get_api_version_from_path(path: str) -> str | None:
    """Extract the API version label from a request path, if present."""
    match = API_VERSION_PREFIX_PATTERN.match(path)
    if match is None:
        return None
    return f"v{match.group('version')}"


def is_supported_api_version(version: str) -> bool:
    """Return whether the provided API version is supported."""
    return version in SUPPORTED_API_VERSIONS


def get_openapi_version() -> str:
    """Return the OpenAPI document version string."""
    return __version__
