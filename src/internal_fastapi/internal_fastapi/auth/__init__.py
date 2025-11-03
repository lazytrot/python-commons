"""Auth module for internal_fastapi."""

from .config import AppTokenConfig
from .middleware import (
    AppTokenAuth,
    TokenAuthMiddleware,
    add_api_key_security_scheme,
    setup_token_auth,
    apply_token_auth_middleware,
    setup_app_token_auth,
)

__all__ = [
    "AppTokenConfig",
    "AppTokenAuth",
    "TokenAuthMiddleware",
    "add_api_key_security_scheme",
    "setup_token_auth",
    "apply_token_auth_middleware",
    "setup_app_token_auth",
]
