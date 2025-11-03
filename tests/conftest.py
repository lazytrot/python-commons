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
    from sqlalchemy.ext.asyncio import AsyncSession
    from internal_rdbms import DatabaseConfig, DatabaseDriver, DatabaseSessionManager, Base
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
            driver=DatabaseDriver.POSTGRESQL,
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            user=postgres_container.username,
            password=postgres_container.password,
            name=postgres_container.dbname,
            echo=True,
        )


    @pytest_asyncio.fixture
    async def db_session(postgres_config):
        """
        Provide database session with automatic table creation/cleanup.

        Uses real PostgreSQL from testcontainers.
        """
        db_manager = DatabaseSessionManager(postgres_config)

        # Create all tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Provide session
        async with db_manager() as session:
            yield session

        # Cleanup
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)

        await db_manager.close()


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

    @pytest.fixture
    def sqlite_memory_config():
        """SQLite in-memory config for fast unit tests."""
        return DatabaseConfig(
            driver=DatabaseDriver.SQLITE_MEMORY,
            echo=True,
        )


    @pytest_asyncio.fixture
    async def sqlite_session(sqlite_memory_config):
        """Fast in-memory database session for unit tests."""
        db_manager = DatabaseSessionManager(sqlite_memory_config)

        # Create all tables
        async with db_manager.engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Provide session
        async with db_manager() as session:
            yield session

        await db_manager.close()
