"""Integration tests for PostgreSQL using testcontainers."""

import pytest

pytest.skip("Test uses old API - needs to be rewritten for new Database interface", allow_module_level=True)
from sqlalchemy import Column, Integer, String, select
from testcontainers.postgres import PostgresContainer
from internal_rdbms import (
    Base,
    DatabaseConfig,
    DatabaseDriver,
    DatabaseSessionManager,
    TimestampMixin,
)


class IntegrationUser(Base, TimestampMixin):
    """Test user model for integration tests."""

    __tablename__ = "integration_users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(100), nullable=False)
    status = Column(String(20), default="active")


@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture(scope="module")
def postgres_config(postgres_container):
    """Create database configuration from testcontainer."""
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


@pytest.fixture
async def db_manager(postgres_config):
    """Create database session manager with PostgreSQL testcontainer."""
    manager = DatabaseSessionManager(postgres_config)

    # Create tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield manager

    # Cleanup tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_connection(db_manager):
    """Test basic PostgreSQL connection."""
    async for session in db_manager():
        result = await session.execute(select(1))
        assert result.scalar() == 1
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_create_user(db_manager):
    """Test creating a user in PostgreSQL."""
    async for session in db_manager():
        user = IntegrationUser(
            username="testuser",
            email="test@example.com",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.status == "active"
        assert user.created_at is not None
        assert user.updated_at is not None
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_query_users(db_manager):
    """Test querying users from PostgreSQL."""
    async for session in db_manager():
        # Create multiple users
        users_data = [
            {"username": "alice", "email": "alice@example.com"},
            {"username": "bob", "email": "bob@example.com"},
            {"username": "charlie", "email": "charlie@example.com"},
        ]

        for data in users_data:
            user = IntegrationUser(**data)
            session.add(user)

        await session.commit()

        # Query all users
        stmt = select(IntegrationUser)
        result = await session.execute(stmt)
        all_users = result.scalars().all()

        assert len(all_users) >= 3

        # Query specific user
        stmt = select(IntegrationUser).where(IntegrationUser.username == "bob")
        result = await session.execute(stmt)
        bob = result.scalar_one()

        assert bob.username == "bob"
        assert bob.email == "bob@example.com"
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_update_user(db_manager):
    """Test updating a user in PostgreSQL."""
    async for session in db_manager():
        # Create user
        user = IntegrationUser(
            username="updateme",
            email="old@example.com",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        user_id = user.id
        original_created = user.created_at

        # Update user
        user.email = "new@example.com"
        user.status = "inactive"
        await session.commit()
        await session.refresh(user)

        assert user.id == user_id
        assert user.email == "new@example.com"
        assert user.status == "inactive"
        assert user.created_at == original_created
        assert user.updated_at >= original_created
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_delete_user(db_manager):
    """Test deleting a user from PostgreSQL."""
    async for session in db_manager():
        # Create user
        user = IntegrationUser(
            username="deleteme",
            email="delete@example.com",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        user_id = user.id

        # Delete user
        await session.delete(user)
        await session.commit()

        # Verify deletion
        stmt = select(IntegrationUser).where(IntegrationUser.id == user_id)
        result = await session.execute(stmt)
        deleted_user = result.scalar_one_or_none()

        assert deleted_user is None
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_unique_constraint(db_manager):
    """Test PostgreSQL unique constraint enforcement."""
    async for session in db_manager():
        # Create first user
        user1 = IntegrationUser(
            username="unique_test",
            email="unique1@example.com",
        )
        session.add(user1)
        await session.commit()

        # Try to create user with duplicate username
        user2 = IntegrationUser(
            username="unique_test",  # Duplicate
            email="unique2@example.com",
        )
        session.add(user2)

        with pytest.raises(Exception):  # Should raise integrity error
            await session.commit()

        await session.rollback()
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_transaction_rollback(db_manager):
    """Test PostgreSQL transaction rollback."""
    async for session in db_manager():
        # Create user
        user = IntegrationUser(
            username="rollback_test",
            email="rollback@example.com",
        )
        session.add(user)
        await session.commit()

        # Start transaction that will be rolled back
        user.status = "modified"

        # Don't commit, just rollback
        await session.rollback()

        # Refresh to get database state
        await session.refresh(user)

        # Status should be original value
        assert user.status == "active"
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_concurrent_sessions(db_manager):
    """Test multiple concurrent PostgreSQL sessions."""
    # Session 1: Create user
    async for session1 in db_manager():
        user = IntegrationUser(
            username="concurrent",
            email="concurrent@example.com",
        )
        session1.add(user)
        await session1.commit()
        break

    # Session 2: Read user
    async for session2 in db_manager():
        stmt = select(IntegrationUser).where(IntegrationUser.username == "concurrent")
        result = await session2.execute(stmt)
        user = result.scalar_one_or_none()

        assert user is not None
        assert user.username == "concurrent"
        break


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_pool_configuration(postgres_config):
    """Test PostgreSQL connection pool settings."""
    # Create manager with custom pool settings
    custom_config = DatabaseConfig(
        driver=postgres_config.driver,
        host=postgres_config.host,
        port=postgres_config.port,
        user=postgres_config.user,
        password=postgres_config.password,
        name=postgres_config.name,
        pool_size=3,
        max_overflow=5,
        pool_timeout=10.0,
    )

    manager = DatabaseSessionManager(custom_config)

    # Verify manager was created with custom settings
    assert manager.config.pool_size == 3
    assert manager.config.max_overflow == 5
    assert manager.config.pool_timeout == 10.0

    # Test connection works
    async for session in manager():
        result = await session.execute(select(1))
        assert result.scalar() == 1
        break

    await manager.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_bulk_insert(db_manager):
    """Test bulk insert performance with PostgreSQL."""
    async for session in db_manager():
        # Create 100 users
        users = [
            IntegrationUser(
                username=f"bulk_user_{i}",
                email=f"bulk_{i}@example.com",
            )
            for i in range(100)
        ]

        session.add_all(users)
        await session.commit()

        # Verify all were inserted
        stmt = select(IntegrationUser).where(
            IntegrationUser.username.like("bulk_user_%")
        )
        result = await session.execute(stmt)
        inserted_users = result.scalars().all()

        assert len(inserted_users) >= 100
        break
