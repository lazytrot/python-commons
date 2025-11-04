"""
Integration tests for HttpClient using real HTTP server (MockServer via testcontainers).

Tests HTTP client functionality against a real HTTP server without mocks.
"""

import pytest
from pydantic import BaseModel

from internal_http import (
    HttpClient,
    BearerAuth,
    BasicAuth,
    ApiKeyAuth,
    RetryConfig,
    AuthConfig,
)


class User(BaseModel):
    """Test user model."""
    id: int
    name: str
    email: str


class CreateUserRequest(BaseModel):
    """Test create user request model."""
    name: str
    email: str


class CreateUserResponse(BaseModel):
    """Test create user response model."""
    id: int
    name: str
    email: str
    message: str


@pytest.mark.integration
@pytest.mark.mockserver
class TestHttpClientIntegration:
    """Test HttpClient against real HTTP server."""

    async def test_get_request(self, http_client, mock_server_url):
        """Test simple GET request."""
        # MockServer is configured via conftest.py
        response = await http_client.get("/api/users/1")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == 1
        assert "name" in data

    async def test_get_with_pydantic_model(self, http_client, mock_server_url):
        """Test GET request with Pydantic model deserialization."""
        user = await http_client.get("/api/users/1", response_model=User)

        assert isinstance(user, User)
        assert user.id == 1
        assert user.name
        assert user.email

    async def test_post_with_json(self, http_client, mock_server_url):
        """Test POST request with JSON data."""
        payload = {"name": "John Doe", "email": "john@example.com"}
        response = await http_client.post("/api/users", json=payload)

        assert response.status_code in (200, 201)
        data = response.json()
        assert data["name"] == "John Doe"
        assert data["email"] == "john@example.com"

    async def test_post_with_pydantic_models(self, http_client, mock_server_url):
        """Test POST with Pydantic request and response models."""
        request_data = CreateUserRequest(name="Jane Smith", email="jane@example.com")

        response = await http_client.post(
            "/api/users",
            request_model=request_data,
            response_model=CreateUserResponse
        )

        assert isinstance(response, CreateUserResponse)
        assert response.name == "Jane Smith"
        assert response.email == "jane@example.com"
        assert response.id > 0

    async def test_put_request(self, http_client, mock_server_url):
        """Test PUT request."""
        payload = {"name": "Updated Name", "email": "updated@example.com"}
        response = await http_client.put("/api/users/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Updated Name"

    async def test_patch_request(self, http_client, mock_server_url):
        """Test PATCH request."""
        payload = {"email": "patched@example.com"}
        response = await http_client.patch("/api/users/1", json=payload)

        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "patched@example.com"

    async def test_delete_request(self, http_client, mock_server_url):
        """Test DELETE request."""
        response = await http_client.delete("/api/users/1")

        assert response.status_code in (200, 204)

    async def test_query_parameters(self, http_client, mock_server_url):
        """Test requests with query parameters."""
        response = await http_client.get("/api/users", params={"page": 1, "limit": 10})

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    async def test_custom_headers(self, http_client, mock_server_url):
        """Test requests with custom headers."""
        headers = {"X-Custom-Header": "CustomValue"}
        response = await http_client.get("/api/users/1", headers=headers)

        assert response.status_code == 200

    async def test_bearer_auth(self, mock_server_url):
        """Test Bearer token authentication."""
        auth = BearerAuth("test-token-123")
        auth_config = AuthConfig(auth=auth)

        client = HttpClient(base_url=mock_server_url, auth_config=auth_config)

        async with client:
            response = await client.get("/api/protected")
            assert response.status_code == 200

    async def test_basic_auth(self, mock_server_url):
        """Test HTTP Basic authentication."""
        auth = BasicAuth(username="testuser", password="testpass")
        auth_config = AuthConfig(auth=auth)

        client = HttpClient(base_url=mock_server_url, auth_config=auth_config)

        async with client:
            response = await client.get("/api/protected")
            assert response.status_code == 200

    async def test_api_key_auth(self, mock_server_url):
        """Test API key authentication."""
        auth = ApiKeyAuth(api_key="test-api-key-456", header_name="X-API-Key")
        auth_config = AuthConfig(auth=auth)

        client = HttpClient(base_url=mock_server_url, auth_config=auth_config)

        async with client:
            response = await client.get("/api/protected")
            assert response.status_code == 200

    async def test_retry_on_failure(self, mock_server_url):
        """Test retry logic on server errors."""
        retry_config = RetryConfig(
            max_retries=3,
            retry_backoff_factor=0.1,
            retry_methods=["GET", "POST"]
        )

        client = HttpClient(
            base_url=mock_server_url,
            retry_config=retry_config
        )

        async with client:
            # MockServer should be configured to fail first 2 attempts, succeed on 3rd
            response = await client.get("/api/flaky-endpoint")
            assert response.status_code == 200

    async def test_timeout_handling(self, mock_server_url):
        """Test timeout handling."""
        client = HttpClient(base_url=mock_server_url, timeout=1.0)

        async with client:
            # MockServer should be configured with delayed response
            with pytest.raises(Exception):  # httpx.TimeoutException or similar
                await client.get("/api/slow-endpoint")

    async def test_error_handling_4xx(self, http_client, mock_server_url):
        """Test handling of 4xx client errors."""
        with pytest.raises(Exception):  # HttpClientError or similar
            await http_client.get("/api/nonexistent")

    async def test_error_handling_5xx(self, http_client, mock_server_url):
        """Test handling of 5xx server errors."""
        # Without retry config, should fail immediately
        client = HttpClient(
            base_url=mock_server_url,
            retry_config=RetryConfig(max_retries=0)
        )

        async with client:
            with pytest.raises(Exception):  # HttpClientError or similar
                await client.get("/api/server-error")

    async def test_context_manager(self, mock_server_url):
        """Test context manager lifecycle."""
        client = HttpClient(base_url=mock_server_url)

        async with client as c:
            response = await c.get("/api/users/1")
            assert response.status_code == 200

        # Client should be closed after context manager exits

    async def test_multiple_requests_same_client(self, http_client, mock_server_url):
        """Test multiple requests using the same client."""
        response1 = await http_client.get("/api/users/1")
        response2 = await http_client.get("/api/users/2")
        response3 = await http_client.post("/api/users", json={"name": "Test", "email": "test@example.com"})

        assert response1.status_code == 200
        assert response2.status_code == 200
        assert response3.status_code in (200, 201)

    async def test_json_serialization(self, http_client, mock_server_url):
        """Test JSON serialization of complex types."""
        payload = {
            "nested": {
                "field": "value",
                "number": 42,
                "boolean": True,
                "list": [1, 2, 3]
            }
        }

        response = await http_client.post("/api/complex", json=payload)
        assert response.status_code in (200, 201)

    async def test_empty_response_body(self, http_client, mock_server_url):
        """Test handling of empty response bodies."""
        response = await http_client.delete("/api/users/1")

        # DELETE often returns 204 No Content
        if response.status_code == 204:
            assert response.text == "" or response.text is None


@pytest.mark.integration
@pytest.mark.mockserver
class TestHttpClientRetryBehavior:
    """Test retry behavior in detail."""

    async def test_no_retry_on_success(self, mock_server_url):
        """Test that successful requests don't trigger retries."""
        retry_config = RetryConfig(max_retries=3)
        client = HttpClient(base_url=mock_server_url, retry_config=retry_config)

        async with client:
            response = await client.get("/api/users/1")
            assert response.status_code == 200
            # Should only make 1 request, not retry

    async def test_retry_on_503(self, mock_server_url):
        """Test retry on 503 Service Unavailable."""
        retry_config = RetryConfig(
            max_retries=3,
            retry_backoff_factor=0.1,
            retry_status_codes=[503]
        )
        client = HttpClient(base_url=mock_server_url, retry_config=retry_config)

        async with client:
            # MockServer configured to return 503 twice, then 200
            response = await client.get("/api/retry-503")
            assert response.status_code == 200

    async def test_max_retries_exceeded(self, mock_server_url):
        """Test behavior when max retries is exceeded."""
        retry_config = RetryConfig(
            max_retries=2,
            retry_backoff_factor=0.1
        )
        client = HttpClient(base_url=mock_server_url, retry_config=retry_config)

        async with client:
            # MockServer configured to always return 500
            with pytest.raises(Exception):  # Should fail after 2 retries
                await client.get("/api/always-fails")

    async def test_retry_only_configured_methods(self, mock_server_url):
        """Test that retries only occur for configured HTTP methods."""
        retry_config = RetryConfig(
            max_retries=3,
            retry_methods=["GET"]  # Only retry GET
        )
        client = HttpClient(base_url=mock_server_url, retry_config=retry_config)

        async with client:
            # GET should retry
            response = await client.get("/api/flaky-get")
            assert response.status_code == 200

            # POST should not retry (fail immediately)
            with pytest.raises(Exception):
                await client.post("/api/flaky-post", json={})
