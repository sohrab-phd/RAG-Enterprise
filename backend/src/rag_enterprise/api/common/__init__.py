"""Reusable API infrastructure."""

from rag_enterprise.api.common.context import (
    CORRELATION_ID_HEADER,
    REQUEST_ID_HEADER,
    get_correlation_id,
    get_request_id,
)
from rag_enterprise.api.common.errors import (
    ApplicationException,
    ErrorDetail,
    ErrorEnvelope,
    UnexpectedError,
    error_response,
    from_application_error,
    status_code_for_error,
)
from rag_enterprise.api.common.handlers import register_exception_handlers
from rag_enterprise.api.common.middleware import RequestContextMiddleware, RequestLoggingMiddleware
from rag_enterprise.api.common.openapi import configure_openapi
from rag_enterprise.api.common.pagination import PaginatedEnvelope, paginated_response
from rag_enterprise.api.common.responses import SuccessEnvelope, success_response
from rag_enterprise.api.common.versioning import (
    CURRENT_API_VERSION,
    SUPPORTED_API_VERSIONS,
    build_versioned_path,
    get_api_version_from_path,
)

__all__ = [
    "CORRELATION_ID_HEADER",
    "CURRENT_API_VERSION",
    "REQUEST_ID_HEADER",
    "SUPPORTED_API_VERSIONS",
    "ApplicationException",
    "ErrorDetail",
    "ErrorEnvelope",
    "PaginatedEnvelope",
    "RequestContextMiddleware",
    "RequestLoggingMiddleware",
    "SuccessEnvelope",
    "UnexpectedError",
    "build_versioned_path",
    "configure_openapi",
    "error_response",
    "from_application_error",
    "get_api_version_from_path",
    "get_correlation_id",
    "get_request_id",
    "paginated_response",
    "register_exception_handlers",
    "status_code_for_error",
    "success_response",
]
