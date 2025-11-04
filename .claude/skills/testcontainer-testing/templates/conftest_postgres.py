"""PostgreSQL testcontainer fixtures template."""

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy import Column, Integer, String
from internal_rdbms import (
    Base,
    DatabaseConfig,
    DatabaseDriver,
    DatabaseSessionManager,
    TimestampMixin,
)


# TODO: Define your models here
class YourModel(Base, TimestampMixin):
    """Replace with your actual model."""

    __tablename__ = "your_table"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    # Add your columns here


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for test session.

    Session scope = container starts once for all tests.
    Fast and efficient.
    """
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture
def postgres_config(postgres_container):
    """Create database configuration from container.

    Function scope = each test can customize if needed.
    """
    return DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
        pool_size=5,
        max_overflow=10,
    )


@pytest_asyncio.fixture
async def db_session(postgres_config):
    """Create database session with automatic table setup/cleanup.

    Function scope = each test gets clean database state.
    """
    manager = DatabaseSessionManager(postgres_config)

    # Create tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager() as session:
        yield session

    # Cleanup: drop tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await manager.close()
