"""
internal_http - HTTP client utilities package.

Provides async HTTP client with authentication, retry logic, and Pydantic model support.
"""

from .auth import AuthBase, BearerAuth, BasicAuth, ApiKeyAuth
from .models import RetryConfig, AuthConfig
from .client import HttpClient, HttpClientError

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
