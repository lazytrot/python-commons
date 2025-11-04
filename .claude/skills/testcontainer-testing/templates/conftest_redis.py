"""Redis testcontainer fixtures template."""

import pytest
import pytest_asyncio
from testcontainers.redis import RedisContainer
from internal_cache import RedisClient, RedisConfig


@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for test session.

    Session scope = container starts once for all tests.
    Fast and efficient.
    """
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    yield redis

    redis.stop()


@pytest.fixture
def redis_config(redis_container):
    """Create Redis configuration from container.

    Function scope = each test can customize db number or other settings.
    """
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
        ssl=False,
    )


@pytest_asyncio.fixture
async def redis_client(redis_config):
    """Create Redis client with automatic cleanup.

    Function scope = each test gets clean Redis state.
    """
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database to clean state
    await client.client.flushdb()
    await client.close()
