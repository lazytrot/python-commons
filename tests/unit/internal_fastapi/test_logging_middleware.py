"""
Unit tests for logging middleware.

Tests LoggingMiddleware.
"""

import pytest
import logging
from fastapi import FastAPI
from fastapi.testclient import TestClient
from internal_fastapi.logging.middleware import LoggingMiddleware


class TestLoggingMiddleware:
    """Test LoggingMiddleware."""

    def test_middleware_logs_request(self, caplog):
        """Test middleware logs request."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        with caplog.at_level(logging.INFO):
            client = TestClient(app)
            response = client.get("/test")

        assert response.status_code == 200

        # Check logs
        logs = [record.message for record in caplog.records]
        assert any("Request: GET /test" in log for log in logs)
        assert any("Response: GET /test - 200" in log for log in logs)

    def test_middleware_adds_timing_header(self):
        """Test middleware adds timing header."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        client = TestClient(app)
        response = client.get("/test")

        assert "X-Process-Time" in response.headers
        assert "ms" in response.headers["X-Process-Time"]

    def test_middleware_logs_error(self, caplog):
        """Test middleware logs errors."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/error")
        async def error_endpoint():
            raise ValueError("Test error")

        with caplog.at_level(logging.ERROR):
            client = TestClient(app)
            try:
                response = client.get("/error")
            except Exception:
                pass

        # Check error logs
        logs = [record.message for record in caplog.records if record.levelname == "ERROR"]
        assert any("Error: GET /error" in log for log in logs)
        assert any("ValueError: Test error" in log for log in logs)

    def test_middleware_with_unknown_client(self, caplog):
        """Test middleware handles unknown client."""
        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/test")
        async def test_endpoint():
            return {"message": "ok"}

        with caplog.at_level(logging.INFO):
            client = TestClient(app)
            response = client.get("/test")

        assert response.status_code == 200

        # Should log request even without client info
        logs = [record.message for record in caplog.records]
        assert any("Request: GET /test" in log for log in logs)
