"""Fixtures for internal_http integration tests."""

import pytest
import time
import requests
from testcontainers.core.container import DockerContainer
from mockserver import MockServerClient

from internal_http import HttpClient, RetryConfig


@pytest.fixture(scope="session")
def mockserver_container():
    """Start MockServer container for HTTP mocking."""
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()

    # Wait for MockServer to be ready by checking if it responds
    host = container.get_container_host_ip()
    port = container.get_exposed_port(1080)
    url = f"http://{host}:{port}"

    for _ in range(30):  # Try for 30 seconds
        try:
            # MockServer should respond to any request, even if it's not mocked
            response = requests.put(f"{url}/status", timeout=1.0)
            # Any response (even 404) means the server is up
            break
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(1)
    else:
        container.stop()
        raise RuntimeError("MockServer container failed to start")

    yield container

    container.stop()


@pytest.fixture(scope="session")
def mock_server_url(mockserver_container):
    """Get MockServer URL."""
    host = mockserver_container.get_container_host_ip()
    port = mockserver_container.get_exposed_port(1080)
    return f"http://{host}:{port}"


@pytest.fixture
def mockserver_client(mock_server_url):
    """Create MockServer client for setting up expectations."""
    client = MockServerClient(mock_server_url)
    yield client
    # Reset expectations after each test
    try:
        client.reset()
    except Exception:
        # Ignore reset errors (container might be stopped)
        pass


@pytest.fixture
async def http_client(mock_server_url):
    """Create HTTP client pointing to MockServer."""
    client = HttpClient(base_url=mock_server_url)
    async with client:
        yield client
