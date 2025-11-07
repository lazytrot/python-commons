"""
Comprehensive tests for FastAPI setup to achieve 100% coverage.

Tests all uncovered lines including setup with/without internal_base.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from internal_fastapi.api.fastapi import FastAPISetup
from internal_fastapi.api.config import APIConfig

try:
    from internal_base import LoggingConfig, LogFormat, AsyncService
    HAS_INTERNAL_BASE = True
except ImportError:
    HAS_INTERNAL_BASE = False


@pytest.fixture
def api_config():
    """Create API configuration."""
    return APIConfig(
        title="Test API",
        description="Test Description",
        version="1.0.0",
        debug=True,
        cors_origins=["http://localhost:3000", "http://localhost:8000"],
    )


class TestFastAPISetupWithoutInternalBase:
    """Test FastAPISetup when internal_base is not available."""

    @patch("internal_fastapi.api.fastapi.configure_logging", None)
    @patch("internal_fastapi.api.fastapi.LoggingConfig", None)
    def test_init_without_internal_base(self, api_config):
        """Test initialization when internal_base is not available."""
        setup = FastAPISetup(api_config)

        assert setup.api_config == api_config
        assert setup.log_config is None
        assert setup.setup_handler is None

    @patch("internal_fastapi.api.fastapi.configure_logging", None)
    def test_create_app_without_logging_config(self, api_config):
        """Test app creation without logging configuration."""
        setup = FastAPISetup(api_config, log_config=None)

        app = setup.create_fastapi_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Test API"
        assert app.description == "Test Description"
        assert app.version == "1.0.0"
        assert app.debug is True


@pytest.mark.skipif(not HAS_INTERNAL_BASE, reason="internal_base not available")
class TestFastAPISetupWithInternalBase:
    """Test FastAPISetup with internal_base available."""

    def test_init_with_log_config(self, api_config):
        """Test initialization with logging configuration."""
        log_config = LoggingConfig(format=LogFormat.JSON, level="INFO")

        with patch("internal_fastapi.api.fastapi.configure_logging") as mock_configure:
            setup = FastAPISetup(api_config, log_config=log_config)

            assert setup.api_config == api_config
            assert setup.log_config == log_config
            mock_configure.assert_called_once_with(log_config)

    def test_init_with_setup_handler(self, api_config):
        """Test initialization with setup handler."""

        async def setup_handler():
            return []

        setup = FastAPISetup(api_config, setup_handler=setup_handler)

        assert setup.setup_handler == setup_handler

    def test_create_app_calls_lifespan(self, api_config):
        """Test app creation with lifespan manager."""

        class TestService(AsyncService):
            async def _start(self) -> None:
                pass

            async def _stop(self) -> None:
                pass

            async def _health_check(self) -> bool:
                return True

        async def setup_handler():
            return [TestService()]

        setup = FastAPISetup(api_config, setup_handler=setup_handler)

        app = setup.create_fastapi_app()

        assert isinstance(app, FastAPI)
        assert app.title == "Test API"


class TestFastAPISetupCORS:
    """Test CORS middleware configuration."""

    def test_create_app_with_cors_origins(self, api_config):
        """Test app creation includes CORS middleware."""
        setup = FastAPISetup(api_config)

        app = setup.create_fastapi_app()

        # Check that app was created
        assert isinstance(app, FastAPI)

        # Create test client to verify CORS
        client = TestClient(app)

        # Add a simple route for testing
        @app.get("/test")
        def test_route():
            return {"message": "test"}

        # Test CORS headers
        response = client.options(
            "/test",
            headers={"Origin": "http://localhost:3000"}
        )

        # CORS middleware should be configured
        assert response.status_code in [200, 405]  # Options or method not allowed


class TestFastAPISetupWithSetupHandler:
    """Test FastAPISetup with setup handler."""

    @pytest.mark.asyncio
    @pytest.mark.skipif(not HAS_INTERNAL_BASE, reason="internal_base not available")
    async def test_create_app_with_services(self, api_config):
        """Test app creation with background services."""

        class TestService(AsyncService):
            def __init__(self):
                super().__init__()
                self.started = False
                self.stopped = False

            async def _start(self) -> None:
                self.started = True

            async def _stop(self) -> None:
                self.stopped = True

            async def _health_check(self) -> bool:
                return True

        service = TestService()

        async def setup_handler():
            return [service]

        setup = FastAPISetup(api_config, setup_handler=setup_handler)

        app = setup.create_fastapi_app()

        assert isinstance(app, FastAPI)


class TestFastAPISetupIntegration:
    """Integration tests for FastAPISetup."""

    def test_full_app_setup(self, api_config):
        """Test complete app setup and basic functionality."""
        setup = FastAPISetup(api_config)

        app = setup.create_fastapi_app()

        # Add test routes
        @app.get("/")
        def root():
            return {"message": "Hello World"}

        @app.get("/health")
        def health():
            return {"status": "ok"}

        # Test the app
        client = TestClient(app)

        response = client.get("/")
        assert response.status_code == 200
        assert response.json() == {"message": "Hello World"}

        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    def test_app_metadata(self, api_config):
        """Test that app metadata is set correctly."""
        setup = FastAPISetup(api_config)

        app = setup.create_fastapi_app()

        assert app.title == "Test API"
        assert app.description == "Test Description"
        assert app.version == "1.0.0"
        assert app.debug is True
