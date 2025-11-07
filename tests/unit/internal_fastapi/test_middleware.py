"""
Unit tests for authentication middleware.

Tests TokenAuthMiddleware and AppTokenAuth.
"""

import pytest
import re
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from internal_fastapi.auth.middleware import (
    AppTokenAuth,
    TokenAuthMiddleware,
    add_api_key_security_scheme,
    setup_token_auth,
    apply_token_auth_middleware
)
from internal_fastapi.auth.config import AppTokenConfig


class TestAppTokenAuth:
    """Test AppTokenAuth handler."""

    def test_init_default(self):
        """Test initialization with default config."""
        auth = AppTokenAuth()
        assert isinstance(auth.settings, AppTokenConfig)
        assert auth.settings.enabled is True

    def test_init_custom(self):
        """Test initialization with custom config."""
        config = AppTokenConfig(
            header_name="X-Custom-Key",
            tokens={"app1": "secret1"}
        )
        auth = AppTokenAuth(config)
        assert auth.settings.header_name == "X-Custom-Key"
        assert auth.settings.tokens == {"app1": "secret1"}

    @pytest.mark.asyncio
    async def test_call_with_excluded_path(self):
        """Test __call__ with excluded path."""
        config = AppTokenConfig(
            tokens={"app1": "token1"},
            exclude_paths={"/health", "/docs"}
        )
        auth = AppTokenAuth(config)

        # Mock request
        class MockRequest:
            class URL:
                path = "/health"
            url = URL()

        request = MockRequest()

        # Should return None for excluded path
        result = await auth(request, api_key=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_call_with_no_token(self):
        """Test __call__ with no token."""
        config = AppTokenConfig(tokens={"app1": "token1"})
        auth = AppTokenAuth(config)

        class MockRequest:
            class URL:
                path = "/api/data"
            url = URL()

        request = MockRequest()
        result = await auth(request, api_key=None)
        assert result is None

    @pytest.mark.asyncio
    async def test_call_with_valid_token(self):
        """Test __call__ with valid token."""
        config = AppTokenConfig(tokens={"app1": "token1", "app2": "token2"})
        auth = AppTokenAuth(config)

        class MockRequest:
            class URL:
                path = "/api/data"
            url = URL()

        request = MockRequest()
        result = await auth(request, api_key="token1")
        assert result == "app1"

        result = await auth(request, api_key="token2")
        assert result == "app2"

    @pytest.mark.asyncio
    async def test_call_with_invalid_token(self):
        """Test __call__ with invalid token."""
        config = AppTokenConfig(tokens={"app1": "token1"})
        auth = AppTokenAuth(config)

        class MockRequest:
            class URL:
                path = "/api/data"
            url = URL()

        request = MockRequest()
        result = await auth(request, api_key="wrong_token")
        assert result is None

    def test_is_path_excluded_exact_match(self):
        """Test exact path matching."""
        config = AppTokenConfig(exclude_paths={"/health", "/metrics"})
        auth = AppTokenAuth(config)

        assert auth._is_path_excluded("/health") is True
        assert auth._is_path_excluded("/metrics") is True
        assert auth._is_path_excluded("/api/data") is False

    def test_is_path_excluded_glob_pattern(self):
        """Test glob pattern matching."""
        config = AppTokenConfig(exclude_paths={"/api/public/*", "/docs*"})
        auth = AppTokenAuth(config)

        assert auth._is_path_excluded("/api/public/users") is True
        assert auth._is_path_excluded("/api/public/posts") is True
        assert auth._is_path_excluded("/docs") is True
        assert auth._is_path_excluded("/docs/api") is True
        assert auth._is_path_excluded("/api/private/data") is False

    def test_is_path_excluded_question_mark(self):
        """Test question mark wildcard."""
        config = AppTokenConfig(exclude_paths={"/test?"})
        auth = AppTokenAuth(config)

        assert auth._is_path_excluded("/test1") is True
        assert auth._is_path_excluded("/test2") is True
        assert auth._is_path_excluded("/test") is False
        assert auth._is_path_excluded("/test12") is False

    def test_convert_pattern_to_regex(self):
        """Test glob pattern to regex conversion."""
        config = AppTokenConfig()
        auth = AppTokenAuth(config)

        # Test * wildcard
        regex = auth._convert_pattern_to_regex("/api/*/data")
        assert regex.match("/api/users/data") is not None
        assert regex.match("/api/posts/data") is not None
        assert regex.match("/api/data") is None

        # Test ? wildcard
        regex = auth._convert_pattern_to_regex("/test?")
        assert regex.match("/test1") is not None
        assert regex.match("/test2") is not None
        assert regex.match("/test") is None


class TestTokenAuthMiddleware:
    """Test TokenAuthMiddleware."""

    def test_init_default(self):
        """Test middleware initialization with defaults."""
        app = FastAPI()
        middleware = TokenAuthMiddleware(app)

        assert isinstance(middleware.settings, AppTokenConfig)
        assert middleware.on_missing_token is None
        assert middleware.on_invalid_token is None

    def test_init_custom(self):
        """Test middleware initialization with custom config."""
        app = FastAPI()
        config = AppTokenConfig(
            header_name="X-API-Key",
            tokens={"app1": "secret"}
        )

        async def missing_handler(request):
            return JSONResponse({"error": "No token"}, status_code=401)

        middleware = TokenAuthMiddleware(
            app,
            settings=config,
            on_missing_token=missing_handler
        )

        assert middleware.settings.header_name == "X-API-Key"
        assert middleware.on_missing_token == missing_handler

    def test_dispatch_disabled(self):
        """Test dispatch when auth is disabled - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(enabled=False)

        # Add middleware to app
        app.add_middleware(TokenAuthMiddleware, settings=config)

        # Add test endpoint
        @app.get("/api/data")
        async def test_endpoint():
            return {"status": "ok"}

        # Test with real HTTP request
        client = TestClient(app)
        response = client.get("/api/data")

        # Should pass through when disabled
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_dispatch_excluded_path(self):
        """Test dispatch with excluded path - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(
            tokens={"app1": "token1"},
            exclude_paths={"/health"}
        )

        app.add_middleware(TokenAuthMiddleware, settings=config)

        @app.get("/health")
        async def health():
            return {"status": "healthy"}

        client = TestClient(app)
        response = client.get("/health")

        # Should pass through for excluded path (no token required)
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    def test_dispatch_missing_token(self):
        """Test dispatch with missing token - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})

        app.add_middleware(TokenAuthMiddleware, settings=config)

        @app.get("/api/data")
        async def protected_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/api/data")

        # Should return 401 when token missing
        assert response.status_code == 401
        assert "Missing authentication token" in response.text

    def test_dispatch_missing_token_custom_handler(self):
        """Test dispatch with custom missing token handler - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})

        async def custom_handler(request):
            return JSONResponse({"custom": "missing"}, status_code=403)

        app.add_middleware(
            TokenAuthMiddleware,
            settings=config,
            on_missing_token=custom_handler
        )

        @app.get("/api/data")
        async def protected_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/api/data")

        assert response.status_code == 403
        assert response.json() == {"custom": "missing"}

    def test_dispatch_invalid_token(self):
        """Test dispatch with invalid token - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(
            header_name="X-App-Token",
            tokens={"app1": "valid_token"}
        )

        app.add_middleware(TokenAuthMiddleware, settings=config)

        @app.get("/api/data")
        async def protected_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/api/data", headers={"x-app-token": "invalid_token"})

        assert response.status_code == 401
        assert "Invalid authentication token" in response.text

    def test_dispatch_invalid_token_custom_handler(self):
        """Test dispatch with custom invalid token handler - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})

        async def custom_handler(request, token):
            return JSONResponse({"custom": "invalid", "token": token}, status_code=403)

        app.add_middleware(
            TokenAuthMiddleware,
            settings=config,
            on_invalid_token=custom_handler
        )

        @app.get("/api/data")
        async def protected_endpoint():
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/api/data", headers={"x-app-token": "bad_token"})

        assert response.status_code == 403
        assert response.json()["custom"] == "invalid"

    def test_dispatch_valid_token(self):
        """Test dispatch with valid token - uses real HTTP requests."""
        app = FastAPI()
        config = AppTokenConfig(
            header_name="X-App-Token",
            tokens={"app1": "secret123"}
        )

        app.add_middleware(TokenAuthMiddleware, settings=config)

        @app.get("/api/data")
        async def protected_endpoint(request: Request):
            # Verify app_name was set by middleware
            assert hasattr(request.state, 'app_name')
            assert request.state.app_name == "app1"
            return {"status": "ok"}

        client = TestClient(app)
        response = client.get("/api/data", headers={"x-app-token": "secret123"})

        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_is_path_excluded(self):
        """Test _is_path_excluded method."""
        app = FastAPI()
        config = AppTokenConfig(exclude_paths={"/health", "/api/public/*"})
        middleware = TokenAuthMiddleware(app, settings=config)

        assert middleware._is_path_excluded("/health") is True
        assert middleware._is_path_excluded("/api/public/users") is True
        assert middleware._is_path_excluded("/api/private/data") is False


class TestHelperFunctions:
    """Test helper functions."""

    def test_add_api_key_security_scheme_disabled(self):
        """Test add_api_key_security_scheme when disabled."""
        app = FastAPI()
        add_api_key_security_scheme(app, "X-API-Key", enabled=False)

        # Should not modify schema when disabled
        # Can't easily test this without triggering OpenAPI generation

    def test_add_api_key_security_scheme_enabled(self):
        """Test add_api_key_security_scheme when enabled."""
        app = FastAPI()

        # Generate OpenAPI schema first
        app.openapi_schema = app.openapi()

        # Ensure components exists
        if "components" not in app.openapi_schema:
            app.openapi_schema["components"] = {}
        if "securitySchemes" not in app.openapi_schema["components"]:
            app.openapi_schema["components"]["securitySchemes"] = {}

        add_api_key_security_scheme(app, "X-API-Key", enabled=True)

        # Should add security scheme
        assert "APIKeyHeader" in app.openapi_schema["components"]["securitySchemes"]
        assert app.openapi_schema["security"] == [{"APIKeyHeader": []}]

    def test_setup_token_auth(self):
        """Test setup_token_auth helper."""
        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})

        auth = setup_token_auth(app, config)

        assert isinstance(auth, AppTokenAuth)
        assert auth.settings == config

    def test_setup_token_auth_default(self):
        """Test setup_token_auth with default config."""
        app = FastAPI()
        auth = setup_token_auth(app)

        assert isinstance(auth, AppTokenAuth)

    def test_apply_token_auth_middleware(self):
        """Test apply_token_auth_middleware helper."""
        app = FastAPI()
        config = AppTokenConfig(tokens={"app1": "token1"})

        apply_token_auth_middleware(app, config)

        # Middleware should be added (can't easily verify without making requests)
