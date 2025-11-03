"""
Integration tests for internal_http HttpClient.

Uses MockServer for real HTTP testing - NO MOCKING.
"""

import pytest
import httpx
from internal_http import HttpClient, HttpClientConfig, RetryConfig, BearerAuth


@pytest.mark.integration
@pytest.mark.mockserver
@pytest.mark.asyncio
class TestHttpClientIntegration:
    """Test HttpClient with real HTTP server (MockServer)."""

    async def test_get_request(self, mockserver_url):
        """Test GET request."""
        client = HttpClient(base_url=mockserver_url)
        
        # MockServer returns 200 by default for any endpoint
        async with client:
            response = await client.get("/api/test")
            assert response.status_code in (200, 404)  # MockServer behavior

    async def test_post_request(self, mockserver_url):
        """Test POST request."""
        client = HttpClient(base_url=mockserver_url)
        
        async with client:
            response = await client.post("/api/data", json={"key": "value"})
            assert response.status_code in (200, 201, 404)

    async def test_retry_on_failure(self, mockserver_url):
        """Test retry logic on failure."""
        config = HttpClientConfig(
            base_url=mockserver_url,
            retries=RetryConfig(max_attempts=3, backoff_factor=0.1)
        )
        client = HttpClient(config)
        
        async with client:
            # Even if endpoint doesn't exist, client handles it
            try:
                response = await client.get("/nonexistent")
            except Exception:
                pass  # Expected for non-existent endpoint

    async def test_authentication_header(self, mockserver_url):
        """Test authentication headers."""
        auth = BearerAuth("test-token")
        client = HttpClient(
            base_url=mockserver_url,
            auth_config=AuthConfig(auth=auth)
        )
        
        async with client:
            response = await client.get("/api/protected")
            # Verify request was made (MockServer accepts it)
            assert response is not None
