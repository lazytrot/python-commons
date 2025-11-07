"""
Shared pytest fixtures for integration tests.

Uses testcontainers and LocalStack for real service testing.
Avoids mocking - tests against actual infrastructure.
"""

import pytest
import pytest_asyncio

try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    from internal_rdbms import DatabaseConfig
    from internal_cache import RedisClient, RedisConfig
    HAS_INTEGRATION_DEPS = True
except ImportError:
    HAS_INTEGRATION_DEPS = False


# Only define fixtures if integration dependencies are available
if HAS_INTEGRATION_DEPS:
    # PostgreSQL fixtures

    @pytest.fixture(scope="session")
    def postgres_container():
        """Start PostgreSQL container for the test session."""
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres


    @pytest.fixture
    def postgres_config(postgres_container):
        """Create PostgreSQL configuration from test container."""
        return DatabaseConfig(
            driver="postgresql+asyncpg",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            user=postgres_container.username,
            password=postgres_container.password,
            name=postgres_container.dbname,
            echo=True,
        )


    # db_session fixture removed - individual test modules should create their own
    # database instances with their specific models


    # Redis fixtures

    @pytest.fixture(scope="session")
    def redis_container():
        """Start Redis container for the test session."""
        with RedisContainer("redis:7-alpine") as redis:
            yield redis


    @pytest.fixture
    def redis_config(redis_container):
        """Create Redis configuration from test container."""
        return RedisConfig(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            db=0,
        )


    @pytest_asyncio.fixture
    async def redis_client(redis_config):
        """
        Provide Redis client connected to real Redis container.

        No mocking - tests against actual Redis instance.
        """
        client = RedisClient(redis_config)
        await client.connect()

        yield client

        # Cleanup: flush database
        await client.client.flushdb()
        await client.close()


    # SQLite in-memory fixtures (for fast unit tests)

    # SQLite fixtures removed - individual test modules should create their own
    # database instances with their specific models
