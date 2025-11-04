"""
internal_http - HTTP client utilities package.

Provides async HTTP client with authentication, retry logic, and Pydantic model support.
"""

from .internal_http import (
    AuthBase,
    BearerAuth,
    BasicAuth,
    ApiKeyAuth,
    RetryConfig,
    AuthConfig,
    HttpClient,
    HttpClientError,
)

__all__ = [
    # Auth
    "AuthBase",
    "BearerAuth",
    "BasicAuth",
    "ApiKeyAuth",
    # Models
    "RetryConfig",
    "AuthConfig",
    # Client
    "HttpClient",
    "HttpClientError",
]
