"""
Token authentication middleware.

Provides token-based authentication middleware for FastAPI.
"""

import re
from typing import Optional, Callable, Awaitable, Any

from fastapi import FastAPI, Request, Response, Header
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.security import APIKeyHeader

from .config import AppTokenConfig


class AppTokenAuth:
    """
    Token authentication handler.

    Validates app tokens from HTTP headers with path exclusion support.

    Example:
        from internal_fastapi import AppTokenAuth, AppTokenConfig

        config = AppTokenConfig(
            header_name="X-API-Key",
            tokens={"app1": "secret1"},
            exclude_paths={"/health", "/docs"}
        )

        auth = AppTokenAuth(config)

        # In FastAPI dependency
        from fastapi import Depends

        @app.get("/protected")
        async def protected_route(app_name: str = Depends(auth)):
            return {"app": app_name}
    """

    def __init__(self, settings: Optional[AppTokenConfig] = None):
        """
        Initialize token auth handler.

        Args:
            settings: Token authentication settings

        Example:
            config = AppTokenConfig(tokens={"app1": "token1"})
            auth = AppTokenAuth(config)
        """
        self.settings = settings or AppTokenConfig()

    async def __call__(
        self,
        request: Request,
        api_key: Optional[str] = Header(None, alias="X-App-Token")
    ) -> Optional[str]:
        """
        Validate token and return app name.

        Args:
            request: FastAPI request
            api_key: API key from header

        Returns:
            App name if valid, None if path excluded

        Raises:
            HTTPException: If token invalid or missing

        Example:
            from fastapi import Depends

            @app.get("/data")
            async def get_data(app_name: str = Depends(auth)):
                return {"app": app_name, "data": [...]}
        """
        # Check if path is excluded
        if self._is_path_excluded(request.url.path):
            return None

        # Validate token
        if not api_key:
            return None

        # Find app name for token
        for app_name, token in self.settings.tokens.items():
            if token == api_key:
                return app_name

        return None

    def _is_path_excluded(self, path: str) -> bool:
        """
        Check if path is excluded from authentication.

        Args:
            path: Request path

        Returns:
            True if path is excluded

        Example:
            # Exact match
            auth._is_path_excluded("/health")  # True if in exclude_paths

            # Glob pattern
            auth._is_path_excluded("/api/public/data")  # True if "/api/public/*" in exclude_paths
        """
        for pattern in self.settings.exclude_paths:
            if "*" in pattern or "?" in pattern:
                # Glob pattern
                regex = self._convert_pattern_to_regex(pattern)
                if regex.match(path):
                    return True
            else:
                # Exact match
                if path == pattern:
                    return True

        return False

    def _convert_pattern_to_regex(self, pattern: str) -> re.Pattern:
        """
        Convert glob pattern to regex.

        Args:
            pattern: Glob pattern

        Returns:
            Compiled regex pattern

        Example:
            regex = auth._convert_pattern_to_regex("/api/*/data")
            regex.match("/api/users/data")  # Match
        """
        # Escape special regex chars except * and ?
        pattern = re.escape(pattern)
        # Convert glob wildcards to regex
        pattern = pattern.replace(r"\*", ".*").replace(r"\?", ".")
        return re.compile(f"^{pattern}$")


class TokenAuthMiddleware(BaseHTTPMiddleware):
    """
    Token authentication middleware.

    Middleware that validates tokens for all requests except excluded paths.

    Example:
        from fastapi import FastAPI
        from internal_fastapi import TokenAuthMiddleware, AppTokenConfig

        app = FastAPI()

        config = AppTokenConfig(
            header_name="X-API-Key",
            tokens={"app1": "secret1"},
            exclude_paths={"/health", "/docs", "/openapi.json"}
        )

        app.add_middleware(
            TokenAuthMiddleware,
            settings=config
        )

        @app.get("/protected")
        async def protected():
            return {"message": "You are authenticated!"}
    """

    def __init__(
        self,
        app: Any,
        settings: Optional[AppTokenConfig] = None,
        on_missing_token: Optional[Callable[[Request], Awaitable[Response]]] = None,
        on_invalid_token: Optional[Callable[[Request, str], Awaitable[Response]]] = None,
        setup_openapi_schema: bool = True
    ):
        """
        Initialize token auth middleware.

        Args:
            app: FastAPI application
            settings: Token authentication settings
            on_missing_token: Handler for missing token
            on_invalid_token: Handler for invalid token
            setup_openapi_schema: Add security scheme to OpenAPI

        Example:
            async def handle_missing(request):
                return JSONResponse(
                    {"error": "Token required"},
                    status_code=401
                )

            middleware = TokenAuthMiddleware(
                app,
                settings=config,
                on_missing_token=handle_missing
            )
        """
        super().__init__(app)
        self.settings = settings or AppTokenConfig()
        self.on_missing_token = on_missing_token
        self.on_invalid_token = on_invalid_token

        # Setup OpenAPI security scheme if FastAPI app
        if setup_openapi_schema and isinstance(app, FastAPI):
            self._setup_openapi_schema(app)

    def _setup_openapi_schema(self, app: FastAPI) -> None:
        """
        Add security scheme to OpenAPI schema.

        Args:
            app: FastAPI application

        Example:
            # Adds API key security to OpenAPI/Swagger docs
            self._setup_openapi_schema(app)
        """
        add_api_key_security_scheme(
            app,
            self.settings.header_name,
            self.settings.enabled
        )

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Dispatch request with token validation.

        Args:
            request: Request
            call_next: Next middleware

        Returns:
            Response

        Example:
            # Called automatically by FastAPI middleware system
            response = await middleware.dispatch(request, call_next)
        """
        # Skip if disabled
        if not self.settings.enabled:
            return await call_next(request)

        # Check if path is excluded
        if self._is_path_excluded(request.url.path):
            return await call_next(request)

        # Get token from header
        token = request.headers.get(self.settings.header_name.lower())

        # Missing token
        if not token:
            if self.on_missing_token:
                return await self.on_missing_token(request)
            return JSONResponse(
                {"error": "Missing authentication token"},
                status_code=401
            )

        # Validate token
        app_name = None
        for name, valid_token in self.settings.tokens.items():
            if token == valid_token:
                app_name = name
                break

        # Invalid token
        if not app_name:
            if self.on_invalid_token:
                return await self.on_invalid_token(request, token)
            return JSONResponse(
                {"error": "Invalid authentication token"},
                status_code=401
            )

        # Add app name to request state
        request.state.app_name = app_name

        return await call_next(request)

    def _is_path_excluded(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        for pattern in self.settings.exclude_paths:
            if "*" in pattern or "?" in pattern:
                # Glob pattern
                regex_pattern = re.escape(pattern).replace(r"\*", ".*").replace(r"\?", ".")
                if re.match(f"^{regex_pattern}$", path):
                    return True
            else:
                # Exact match
                if path == pattern:
                    return True
        return False


def add_api_key_security_scheme(
    app: FastAPI,
    header_name: str,
    enabled: bool = True
) -> None:
    """
    Add API key security scheme to OpenAPI.

    Args:
        app: FastAPI application
        header_name: Header name for API key
        enabled: Whether security is enabled

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        add_api_key_security_scheme(app, "X-API-Key")

        # Now Swagger UI will show API key input
    """
    if not enabled:
        return

    # Add security scheme to OpenAPI schema
    if app.openapi_schema:
        app.openapi_schema["components"]["securitySchemes"] = {
            "APIKeyHeader": {
                "type": "apiKey",
                "in": "header",
                "name": header_name
            }
        }
        app.openapi_schema["security"] = [{"APIKeyHeader": []}]


def setup_token_auth(
    app: FastAPI,
    settings: Optional[AppTokenConfig] = None
) -> AppTokenAuth:
    """
    Setup token authentication handler.

    Args:
        app: FastAPI application
        settings: Token authentication settings

    Returns:
        AppTokenAuth instance

    Example:
        from fastapi import FastAPI, Depends

        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})
        auth = setup_token_auth(app, config)

        @app.get("/protected")
        async def protected(app_name: str = Depends(auth)):
            return {"app": app_name}
    """
    settings = settings or AppTokenConfig()
    add_api_key_security_scheme(app, settings.header_name, settings.enabled)
    return AppTokenAuth(settings)


def apply_token_auth_middleware(
    app: FastAPI,
    settings: Optional[AppTokenConfig] = None,
    on_missing_token: Optional[Callable[[Request], Awaitable[Response]]] = None,
    on_invalid_token: Optional[Callable[[Request, str], Awaitable[Response]]] = None
) -> None:
    """
    Apply token authentication middleware.

    Args:
        app: FastAPI application
        settings: Token authentication settings
        on_missing_token: Handler for missing token
        on_invalid_token: Handler for invalid token

    Example:
        from fastapi import FastAPI

        app = FastAPI()
        config = AppTokenConfig(
            tokens={"app1": "secret"},
            exclude_paths={"/health", "/docs"}
        )

        apply_token_auth_middleware(app, config)

        @app.get("/api/data")
        async def get_data():
            return {"data": "protected"}
    """
    app.add_middleware(
        TokenAuthMiddleware,
        settings=settings,
        on_missing_token=on_missing_token,
        on_invalid_token=on_invalid_token
    )


# Alias for backward compatibility
setup_app_token_auth = setup_token_auth
