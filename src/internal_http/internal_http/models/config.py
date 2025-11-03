"""
HTTP client configuration models.

Provides Pydantic models for HTTP client configuration.
"""

from typing import List, Any, Optional, Callable
from pydantic import BaseModel, Field


class RetryConfig(BaseModel):
    """Retry configuration."""

    max_attempts: int = Field(default=3, description="Maximum retry attempts")
    retry_statuses: List[int] = Field(
        default=[500, 502, 503, 504],
        description="HTTP status codes to retry"
    )
    retry_methods: List[str] = Field(
        default=["GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"],
        description="HTTP methods to retry"
    )
    backoff_factor: float = Field(
        default=0.5,
        description="Backoff multiplier between retries"
    )
    jitter: bool = Field(
        default=True,
        description="Add random jitter to backoff"
    )
    retry_exceptions: List[Any] = Field(
        default_factory=list,
        description="Exception types to retry"
    )


class AuthConfig(BaseModel):
    """Authentication configuration."""

    model_config = {"arbitrary_types_allowed": True}

    auth: Optional[Any] = Field(
        default=None,
        description="Authentication instance (BearerAuth, BasicAuth, etc)"
    )
    refresh_token: Optional[str] = Field(
        default=None,
        description="Refresh token for token renewal"
    )
    refresh_callback: Optional[Callable[[], str]] = Field(
        default=None,
        description="Callback function to refresh auth token"
    )
