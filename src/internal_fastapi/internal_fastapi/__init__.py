"""
internal_fastapi - FastAPI utilities package.

Provides FastAPI utilities for authentication, health checks, logging, and lifecycle management.
"""

from .api import (
    APIService,
    APIConfig,
    Environment,
    FastAPISetup,
    LifecycleManager,
)
from .auth import (
    AppTokenConfig,
    AppTokenAuth,
    TokenAuthMiddleware,
    add_api_key_security_scheme,
    setup_token_auth,
    apply_token_auth_middleware,
    setup_app_token_auth,
)
from .health import (
    HealthCheck,
    HealthResponse,
    create_health_endpoint,
)
from .logging import (
    LoggingMiddleware,
)

__all__ = [
    # API
    "APIService",
    "APIConfig",
    "Environment",
    "FastAPISetup",
    "LifecycleManager",
    # Auth
    "AppTokenConfig",
    "AppTokenAuth",
    "TokenAuthMiddleware",
    "add_api_key_security_scheme",
    "setup_token_auth",
    "apply_token_auth_middleware",
    "setup_app_token_auth",
    # Health
    "HealthCheck",
    "HealthResponse",
    "create_health_endpoint",
    # Logging
    "LoggingMiddleware",
]
