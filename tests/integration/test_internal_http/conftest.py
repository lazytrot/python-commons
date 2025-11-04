"""Fixtures for internal_http integration tests."""

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from internal_http import HttpClient, RetryConfig


@pytest.fixture(scope="session")
def mockserver_container():
    """Start MockServer container for HTTP mocking."""
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()

    # Wait for MockServer to be ready
    wait_for_logs(container, "started on port", timeout=30)

    yield container

    container.stop()


@pytest.fixture
def mock_server_url(mockserver_container):
    """Get MockServer URL."""
    host = mockserver_container.get_container_host_ip()
    port = mockserver_container.get_exposed_port(1080)
    return f"http://{host}:{port}"


@pytest.fixture
async def http_client(mock_server_url):
    """Create HTTP client pointing to MockServer."""
    client = HttpClient(base_url=mock_server_url)
    async with client:
        yield client
