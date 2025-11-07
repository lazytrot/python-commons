"""
Integration tests for HttpClient using MockServer.

Tests against MockServer container - NO MOCKING of client code, real HTTP infrastructure.
Uses testcontainers for real HTTP testing with controlled responses.
"""

import pytest
from mockserver import MockServerClient, request as mock_request, response as mock_response, times

from internal_http import HttpClient, BearerAuth, BasicAuth, AuthConfig, RetryConfig, HttpClientError
from pydantic import BaseModel


class User(BaseModel):
    """Test model for JSON responses."""
    name: str
    age: int


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientBasicOperations:
    """Test basic HTTP operations."""

    async def test_get_request(self, mock_server_url, mockserver_client):
        """Test GET request."""
        # Setup mock expectation
        mockserver_client.stub(
            mock_request(method="GET", path="/get"),
            mock_response(code=200, body={"url": f"{mock_server_url}/get", "method": "GET"}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.get("/get")

            assert response.status_code == 200
            data = response.json()
            assert "url" in data
            assert data["method"] == "GET"

    async def test_get_with_params(self, mock_server_url, mockserver_client):
        """Test GET with query parameters."""
        # Setup mock to return query params
        mockserver_client.stub(
            mock_request(method="GET", path="/get", querystring={"foo": "bar", "test": "123"}),
            mock_response(code=200, body={"args": {"foo": "bar", "test": "123"}}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.get("/get", params={"foo": "bar", "test": "123"})

            data = response.json()
            assert data["args"]["foo"] == "bar"
            assert data["args"]["test"] == "123"

    async def test_post_json(self, mock_server_url, mockserver_client):
        """Test POST with JSON body."""
        payload = {"name": "test", "value": 42}

        mockserver_client.stub(
            mock_request(method="POST", path="/post"),
            mock_response(code=200, body=payload),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.post("/post", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data == payload

    async def test_post_data(self, mock_server_url, mockserver_client):
        """Test POST with form data."""
        form_data = {"field1": "value1", "field2": "value2"}

        mockserver_client.stub(
            mock_request(method="POST", path="/post"),
            mock_response(code=200, body={"form": form_data}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.post("/post", data=form_data)

            assert response.status_code == 200
            data = response.json()
            assert data["form"] == form_data

    async def test_put_request(self, mock_server_url, mockserver_client):
        """Test PUT request."""
        payload = {"updated": True}

        mockserver_client.stub(
            mock_request(method="PUT", path="/put"),
            mock_response(code=200, body=payload),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.put("/put", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data == payload

    async def test_patch_request(self, mock_server_url, mockserver_client):
        """Test PATCH request."""
        payload = {"patched": "field"}

        mockserver_client.stub(
            mock_request(method="PATCH", path="/patch"),
            mock_response(code=200, body=payload),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.patch("/patch", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data == payload

    async def test_delete_request(self, mock_server_url, mockserver_client):
        """Test DELETE request."""
        mockserver_client.stub(
            mock_request(method="DELETE", path="/delete"),
            mock_response(code=200),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.delete("/delete")

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientHeaders:
    """Test header handling."""

    async def test_default_headers(self, mock_server_url, mockserver_client):
        """Test default headers are sent."""
        mockserver_client.stub(
            mock_request(method="GET", path="/headers", headers={"X-Custom-Header": "test-value"}),
            mock_response(code=200, body={"headers": {"X-Custom-Header": "test-value"}}),
            times(1)
        )

        default_headers = {"X-Custom-Header": "test-value"}
        async with HttpClient(base_url=mock_server_url, default_headers=default_headers) as client:
            response = await client.get("/headers")

            data = response.json()
            assert data["headers"]["X-Custom-Header"] == "test-value"

    async def test_request_headers(self, mock_server_url, mockserver_client):
        """Test per-request headers."""
        mockserver_client.stub(
            mock_request(method="GET", path="/headers", headers={"X-Request-Header": "request-value"}),
            mock_response(code=200, body={"headers": {"X-Request-Header": "request-value"}}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            headers = {"X-Request-Header": "request-value"}
            response = await client.get("/headers", headers=headers)

            data = response.json()
            assert data["headers"]["X-Request-Header"] == "request-value"


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientAuth:
    """Test authentication."""

    async def test_bearer_auth(self, mock_server_url, mockserver_client):
        """Test Bearer token authentication."""
        mockserver_client.stub(
            mock_request(method="GET", path="/bearer", headers={"Authorization": "Bearer test-token-123"}),
            mock_response(code=200, body={"authenticated": True, "token": "test-token-123"}),
            times(1)
        )

        auth_config = AuthConfig(auth=BearerAuth("test-token-123"))
        async with HttpClient(base_url=mock_server_url, auth_config=auth_config) as client:
            response = await client.get("/bearer")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["token"] == "test-token-123"

    async def test_basic_auth(self, mock_server_url, mockserver_client):
        """Test Basic authentication."""
        mockserver_client.stub(
            mock_request(method="GET", path="/basic-auth"),
            mock_response(code=200, body={"authenticated": True, "user": "user"}),
            times(1)
        )

        auth_config = AuthConfig(auth=BasicAuth("user", "pass"))
        async with HttpClient(base_url=mock_server_url, auth_config=auth_config) as client:
            response = await client.get("/basic-auth")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientRetry:
    """Test retry logic."""

    async def test_retry_on_500(self, mock_server_url, mockserver_client):
        """Test retry on server error."""
        # Mock will return 500 for all 3 attempts
        mockserver_client.stub(
            mock_request(method="GET", path="/status/500"),
            mock_response(code=500),
            times(3)
        )

        retry_config = RetryConfig(max_attempts=3, backoff_factor=0.1)
        client = HttpClient(base_url=mock_server_url, retries=retry_config)

        # Should retry and return 500 response after exhausting retries
        response = await client.get("/status/500")

        assert response.status_code == 500
        await client.close()

    async def test_no_retry_on_404(self, mock_server_url, mockserver_client):
        """Test no retry on client error."""
        # 404 should not be retried - only called once
        mockserver_client.stub(
            mock_request(method="GET", path="/status/404"),
            mock_response(code=404),
            times(1)
        )

        retry_config = RetryConfig(max_attempts=3)
        client = HttpClient(base_url=mock_server_url, retries=retry_config)

        # Should return 404 response without retries
        response = await client.get("/status/404")

        assert response.status_code == 404
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientModels:
    """Test Pydantic model support."""

    async def test_get_model_success(self, mock_server_url, mockserver_client):
        """Test get_model with successful response."""
        mockserver_client.stub(
            mock_request(method="POST", path="/anything"),
            mock_response(code=200, body={"name": "Alice", "age": 30}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.post("/anything", json={"name": "Alice", "age": 30})

            # Manually parse to test concept
            data = response.json()
            user = User(**data)

            assert user.name == "Alice"
            assert user.age == 30

    async def test_post_model(self, mock_server_url, mockserver_client):
        """Test posting a Pydantic model."""
        user = User(name="Bob", age=25)

        mockserver_client.stub(
            mock_request(method="POST", path="/post"),
            mock_response(code=200, body={"name": "Bob", "age": 25}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.post("/post", json=user.model_dump())

            data = response.json()
            assert data["name"] == "Bob"
            assert data["age"] == 25


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientErrorHandling:
    """Test error handling."""

    async def test_connection_error(self):
        """Test connection error handling."""
        client = HttpClient(base_url="http://localhost:1", timeout=1.0)

        with pytest.raises(HttpClientError):
            await client.get("/test")

        await client.close()

    async def test_timeout_error(self, mock_server_url, mockserver_client):
        """Test timeout handling."""
        # Mock with a very long delay response (will timeout)
        mockserver_client.stub(
            mock_request(method="GET", path="/delay"),
            mock_response(code=200, body={"delayed": True}, delay=10000),  # 10 second delay
            times(3)  # Allow for retries
        )

        # Use a short timeout to ensure it times out
        async with HttpClient(base_url=mock_server_url, timeout=0.5) as client:
            with pytest.raises(HttpClientError):
                await client.get("/delay")


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientContextManager:
    """Test context manager functionality."""

    async def test_context_manager_closes_client(self, mock_server_url, mockserver_client):
        """Test context manager properly closes client."""
        mockserver_client.stub(
            mock_request(method="GET", path="/get"),
            mock_response(code=200, body={"success": True}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.get("/get")
            assert response.status_code == 200
            # Client should be open
            assert client._client is not None

        # After exiting context, client should be closed
        # (we can't easily verify this without accessing internals)

    async def test_manual_close(self, mock_server_url, mockserver_client):
        """Test manual close."""
        mockserver_client.stub(
            mock_request(method="GET", path="/get"),
            mock_response(code=200, body={"success": True}),
            times(1)
        )

        client = HttpClient(base_url=mock_server_url)
        response = await client.get("/get")
        assert response.status_code == 200

        await client.close()
        # Client closed
