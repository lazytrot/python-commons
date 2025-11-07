"""
Unit tests for health check endpoint.

Tests HealthCheck and create_health_endpoint.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from internal_fastapi.health.endpoint import (
    HealthCheck,
    HealthResponse,
    create_health_endpoint,
    asyncio_is_coroutine_function
)


class TestHealthResponse:
    """Test HealthResponse model."""

    def test_default_values(self):
        """Test default values."""
        response = HealthResponse()
        assert response.status == "healthy"
        assert response.details == {}

    def test_custom_values(self):
        """Test custom values."""
        details = {"database": {"status": "connected"}}
        response = HealthResponse(status="unhealthy", details=details)
        assert response.status == "unhealthy"
        assert response.details == details


class TestAsyncioIsCoroutineFunction:
    """Test asyncio_is_coroutine_function."""

    def test_sync_function(self):
        """Test with sync function."""
        def sync_func():
            return "sync"

        assert asyncio_is_coroutine_function(sync_func) is False

    def test_async_function(self):
        """Test with async function."""
        async def async_func():
            return "async"

        assert asyncio_is_coroutine_function(async_func) is True


class TestHealthCheck:
    """Test HealthCheck class."""

    def test_init_without_app(self):
        """Test initialization without app."""
        health = HealthCheck(path="/healthz")
        assert health.path == "/healthz"
        assert health.checks == []

    def test_init_with_app(self):
        """Test initialization with app."""
        app = FastAPI()
        health = HealthCheck(app, path="/health")
        assert health.path == "/health"

        # Endpoint should be registered
        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_add_check(self):
        """Test adding a check."""
        health = HealthCheck()

        def check_db():
            return {"status": "connected"}

        health.add_check("database", check_db)

        assert len(health.checks) == 1
        assert health.checks[0][0] == "database"
        assert health.checks[0][1] == check_db

    def test_add_multiple_checks(self):
        """Test adding multiple checks."""
        health = HealthCheck()

        def check_db():
            return {"status": "ok"}

        async def check_redis():
            return {"status": "ok"}

        health.add_check("database", check_db)
        health.add_check("redis", check_redis)

        assert len(health.checks) == 2

    def test_add_to_app(self):
        """Test adding to app."""
        app = FastAPI()
        health = HealthCheck()

        def check_db():
            return {"status": "connected"}

        health.add_check("database", check_db)
        health.add_to_app(app)

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "database" in data["details"]

    def test_health_endpoint_no_checks(self):
        """Test health endpoint with no checks."""
        app = FastAPI()
        health = HealthCheck(app)

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["details"] == {}

    def test_health_endpoint_with_sync_check(self):
        """Test health endpoint with sync check."""
        app = FastAPI()
        health = HealthCheck(app)

        def check_db():
            return {"status": "connected", "connections": 10}

        health.add_check("database", check_db)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["details"]["database"]["status"] == "connected"
        assert data["details"]["database"]["connections"] == 10

    def test_health_endpoint_with_async_check(self):
        """Test health endpoint with async check."""
        app = FastAPI()
        health = HealthCheck(app)

        async def check_cache():
            return {"status": "ok", "keys": 100}

        health.add_check("cache", check_cache)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "healthy"
        assert data["details"]["cache"]["status"] == "ok"

    def test_health_endpoint_check_error(self):
        """Test health endpoint when check raises error."""
        app = FastAPI()
        health = HealthCheck(app)

        def failing_check():
            raise RuntimeError("Database connection failed")

        health.add_check("database", failing_check)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "unhealthy"
        assert data["details"]["database"]["status"] == "error"
        assert "Database connection failed" in data["details"]["database"]["error"]

    def test_health_endpoint_unhealthy_status(self):
        """Test health endpoint with unhealthy check."""
        app = FastAPI()
        health = HealthCheck(app)

        def unhealthy_check():
            return {"status": "error", "message": "Failed"}

        health.add_check("service", unhealthy_check)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert data["status"] == "unhealthy"

    def test_health_endpoint_mixed_checks(self):
        """Test health endpoint with mixed check results."""
        app = FastAPI()
        health = HealthCheck(app)

        def ok_check():
            return {"status": "ok"}

        def down_check():
            return {"status": "down"}

        health.add_check("service1", ok_check)
        health.add_check("service2", down_check)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        # Overall status should be unhealthy if any check is down
        assert data["status"] == "unhealthy"

    def test_add_to_app_include_in_schema(self):
        """Test adding to app with schema inclusion."""
        app = FastAPI()
        health = HealthCheck()
        health.add_to_app(app, include_in_schema=True)

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200


class TestCreateHealthEndpoint:
    """Test create_health_endpoint function."""

    def test_create_default(self):
        """Test create with defaults."""
        app = FastAPI()
        health = create_health_endpoint(app)

        assert isinstance(health, HealthCheck)
        assert health.path == "/health"

        client = TestClient(app)
        response = client.get("/health")
        assert response.status_code == 200

    def test_create_custom_path(self):
        """Test create with custom path."""
        app = FastAPI()
        health = create_health_endpoint(app, path="/healthz")

        client = TestClient(app)
        response = client.get("/healthz")
        assert response.status_code == 200

    def test_create_with_checks(self):
        """Test create with initial checks."""
        app = FastAPI()

        def check_db():
            return {"status": "ok"}

        async def check_cache():
            return {"status": "ok"}

        health = create_health_endpoint(
            app,
            checks=[
                ("database", check_db),
                ("cache", check_cache)
            ]
        )

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert "database" in data["details"]
        assert "cache" in data["details"]

    def test_add_checks_after_creation(self):
        """Test adding checks after creation."""
        app = FastAPI()
        health = create_health_endpoint(app)

        def new_check():
            return {"status": "ok"}

        health.add_check("new_service", new_check)

        client = TestClient(app)
        response = client.get("/health")
        data = response.json()

        assert "new_service" in data["details"]
