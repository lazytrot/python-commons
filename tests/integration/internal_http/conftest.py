"""Fixtures for internal_http integration tests."""

import pytest
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_strategies import wait_for_logs

from internal_http import HttpClient, S3ClientConfig, RetryConfig


@pytest.fixture(scope="session")
def mockserver_container():
    """Start MockServer container for HTTP mocking."""
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()
    
    # Wait for MockServer to be ready
    wait_for_logs(container, "started on port: 1080")
    
    yield container
    
    container.stop()


@pytest.fixture
def mockserver_url(mockserver_container):
    """Get MockServer URL."""
    host = mockserver_container.get_container_host_ip()
    port = mockserver_container.get_exposed_port(1080)
    return f"http://{host}:{port}"


@pytest.fixture
def http_client(mockserver_url):
    """Create HTTP client pointing to MockServer."""
    config = HttpClientConfig(base_url=mockserver_url)
    return HttpClient(config)
