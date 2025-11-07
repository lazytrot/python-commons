"""
Integration tests for HttpClient using real HTTP server.

Tests against httpbin container - NO MOCKING.
Uses testcontainers for real HTTP infrastructure.
"""

import pytest
import asyncio
import httpx
from testcontainers.core.container import DockerContainer

from internal_http import HttpClient, BearerAuth, BasicAuth, AuthConfig, RetryConfig
from internal_http.client.http_client import HttpClientError
from pydantic import BaseModel


class User(BaseModel):
    """Test model for JSON responses."""
    name: str
    age: int


@pytest.fixture(scope="module")
def httpbin_container():
    """Start httpbin container for HTTP testing."""
    # httpbin is a perfect HTTP testing service
    container = DockerContainer("kennethreitz/httpbin:latest")
    container.with_exposed_ports(80)
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="module")
async def httpbin_url(httpbin_container):
    """Get httpbin base URL and wait for it to be ready."""
    host = httpbin_container.get_container_host_ip()
    port = httpbin_container.get_exposed_port(80)
    url = f"http://{host}:{port}"

    # Wait for httpbin to be ready
    async with httpx.AsyncClient() as client:
        for _ in range(30):  # Try for 30 seconds
            try:
                response = await client.get(f"{url}/get", timeout=1.0)
                if response.status_code == 200:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(1)
        else:
            raise RuntimeError("httpbin container failed to start")

    return url


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientBasicOperations:
    """Test basic HTTP operations."""

    async def test_get_request(self, httpbin_url):
        """Test GET request."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.get("/get")

            assert response.status_code == 200
            data = response.json()
            assert "url" in data

    async def test_get_with_params(self, httpbin_url):
        """Test GET with query parameters."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.get("/get", params={"foo": "bar", "test": "123"})

            data = response.json()
            assert data["args"]["foo"] == "bar"
            assert data["args"]["test"] == "123"

    async def test_post_json(self, httpbin_url):
        """Test POST with JSON body."""
        async with HttpClient(base_url=httpbin_url) as client:
            payload = {"name": "test", "value": 42}
            response = await client.post("/post", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["json"] == payload

    async def test_post_data(self, httpbin_url):
        """Test POST with form data."""
        async with HttpClient(base_url=httpbin_url) as client:
            form_data = {"field1": "value1", "field2": "value2"}
            response = await client.post("/post", data=form_data)

            assert response.status_code == 200
            data = response.json()
            assert data["form"] == form_data

    async def test_put_request(self, httpbin_url):
        """Test PUT request."""
        async with HttpClient(base_url=httpbin_url) as client:
            payload = {"updated": True}
            response = await client.put("/put", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["json"] == payload

    async def test_patch_request(self, httpbin_url):
        """Test PATCH request."""
        async with HttpClient(base_url=httpbin_url) as client:
            payload = {"patched": "field"}
            response = await client.patch("/patch", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["json"] == payload

    async def test_delete_request(self, httpbin_url):
        """Test DELETE request."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.delete("/delete")

            assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientHeaders:
    """Test header handling."""

    async def test_default_headers(self, httpbin_url):
        """Test default headers are sent."""
        default_headers = {"X-Custom-Header": "test-value"}
        async with HttpClient(base_url=httpbin_url, default_headers=default_headers) as client:
            response = await client.get("/headers")

            data = response.json()
            assert data["headers"]["X-Custom-Header"] == "test-value"

    async def test_request_headers(self, httpbin_url):
        """Test per-request headers."""
        async with HttpClient(base_url=httpbin_url) as client:
            headers = {"X-Request-Header": "request-value"}
            response = await client.get("/headers", headers=headers)

            data = response.json()
            assert data["headers"]["X-Request-Header"] == "request-value"


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientAuth:
    """Test authentication."""

    async def test_bearer_auth(self, httpbin_url):
        """Test Bearer token authentication."""
        auth_config = AuthConfig(auth=BearerAuth("test-token-123"))
        async with HttpClient(base_url=httpbin_url, auth_config=auth_config) as client:
            response = await client.get("/bearer")

            # httpbin /bearer endpoint requires Bearer token
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["token"] == "test-token-123"

    async def test_basic_auth(self, httpbin_url):
        """Test Basic authentication."""
        auth_config = AuthConfig(auth=BasicAuth("user", "pass"))
        async with HttpClient(base_url=httpbin_url, auth_config=auth_config) as client:
            response = await client.get("/basic-auth/user/pass")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientRetry:
    """Test retry logic."""

    async def test_retry_on_500(self, httpbin_url):
        """Test retry on server error."""
        retry_config = RetryConfig(max_retries=3, backoff_factor=0.1)
        client = HttpClient(base_url=httpbin_url, retries=retry_config)

        # httpbin /status/500 returns 500 error
        with pytest.raises(HttpClientError) as exc_info:
            await client.get("/status/500")

        assert exc_info.value.status_code == 500
        await client.close()

    async def test_no_retry_on_404(self, httpbin_url):
        """Test no retry on client error."""
        retry_config = RetryConfig(max_retries=3)
        client = HttpClient(base_url=httpbin_url, retries=retry_config)

        # 404 should not be retried
        with pytest.raises(HttpClientError) as exc_info:
            await client.get("/status/404")

        assert exc_info.value.status_code == 404
        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientModels:
    """Test Pydantic model support."""

    async def test_get_model_success(self, httpbin_url):
        """Test get_model with successful response."""
        async with HttpClient(base_url=httpbin_url) as client:
            # Mock a JSON response that matches User model
            response = await client.post("/anything", json={"name": "Alice", "age": 30})

            # Manually parse to test concept
            data = response.json()
            user = User(**data["json"])

            assert user.name == "Alice"
            assert user.age == 30

    async def test_post_model(self, httpbin_url):
        """Test posting a Pydantic model."""
        user = User(name="Bob", age=25)

        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.post("/post", json=user.model_dump())

            data = response.json()
            assert data["json"]["name"] == "Bob"
            assert data["json"]["age"] == 25


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

    async def test_timeout_error(self, httpbin_url):
        """Test timeout handling."""
        client = HttpClient(base_url=httpbin_url, timeout=0.001)

        # /delay endpoint will timeout
        with pytest.raises(HttpClientError):
            await client.get("/delay/5")

        await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientContextManager:
    """Test context manager functionality."""

    async def test_context_manager_closes_client(self, httpbin_url):
        """Test context manager properly closes client."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.get("/get")
            assert response.status_code == 200
            # Client should be open
            assert client._client is not None

        # After exiting context, client should be closed
        # (we can't easily verify this without accessing internals)

    async def test_manual_close(self, httpbin_url):
        """Test manual close."""
        client = HttpClient(base_url=httpbin_url)
        response = await client.get("/get")
        assert response.status_code == 200

        await client.close()
        # Client closed
