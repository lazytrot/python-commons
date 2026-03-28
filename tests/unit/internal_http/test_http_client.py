"""
Unit tests for internal_http HttpClient lifecycle behavior.
"""

import pytest
import httpx
from internal_base import ServiceState

from internal_http import HttpClient, RetryConfig


@pytest.mark.asyncio
class TestHttpClientLifecycle:
    """Test HttpClient lifecycle and dependency injection behavior."""

    async def test_start_reuses_injected_client(self):
        """Lifecycle should reuse the injected client instance."""
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(200, json={"ok": True}, request=request)

        async_client = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(handler),
        )
        client = HttpClient(client=async_client)

        await client.start()
        first_client = client._client

        first_response = await client.get("/first")
        second_response = await client.get("/second")

        assert first_response.status_code == 200
        assert second_response.status_code == 200
        assert client._client is first_client
        assert calls["count"] == 2
        assert client.state == ServiceState.RUNNING

        await client.stop()
        assert client.state == ServiceState.STOPPED
        assert client._client is first_client
        assert client._client.is_closed is True

    async def test_request_lazy_starts_service(self):
        """Requests should lazily start the service for backward compatibility."""
        async_client = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"ok": True}, request=request)
            ),
        )
        client = HttpClient(client=async_client)

        response = await client.get("/lazy-start")

        assert response.status_code == 200
        assert client.state == ServiceState.RUNNING

        await client.close()
        assert client.state == ServiceState.STOPPED

    async def test_close_releases_injected_client(self):
        """Closing should dispose the injected client through service lifecycle."""
        async_client = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"ok": True}, request=request)
            ),
        )
        client = HttpClient(client=async_client)

        await client.start()
        injected_client = client._client

        await client.close()

        assert injected_client.is_closed is True
        assert client._client is injected_client
        assert client.state == ServiceState.STOPPED

    async def test_injected_client_is_closed_on_stop(self):
        """Injected DI client is application-owned and closed by the lifecycle."""
        injected_client = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(
                lambda request: httpx.Response(200, json={"ok": True}, request=request)
            ),
        )
        client = HttpClient(client=injected_client)

        await client.start()
        response = await client.get("/injected")
        await client.stop()

        assert response.status_code == 200
        assert client._client is injected_client
        assert injected_client.is_closed is True
        assert client.state == ServiceState.STOPPED

    async def test_closed_injected_client_fails_start(self):
        """A closed injected client should fail fast on startup."""
        injected_client = httpx.AsyncClient()
        await injected_client.aclose()

        client = HttpClient(client=injected_client)

        with pytest.raises(RuntimeError, match="already closed"):
            await client.start()

        assert client.state == ServiceState.FAILED

    async def test_retry_methods_are_respected(self):
        """Retry should only apply to configured HTTP methods."""
        calls = {"count": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            calls["count"] += 1
            return httpx.Response(500, json={"ok": False}, request=request)

        async_client = httpx.AsyncClient(
            base_url="http://testserver",
            transport=httpx.MockTransport(handler),
        )
        client = HttpClient(
            client=async_client,
            retries=RetryConfig(max_attempts=3, retry_methods=["GET"], backoff_factor=0),
        )

        response = await client.post("/no-retry")

        assert response.status_code == 500
        assert calls["count"] == 1

        await client.close()
