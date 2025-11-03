"""Tests for database session management with SQLite in-memory."""

import pytest
from sqlalchemy import Column, Integer, String, select
from internal_rdbms import (
    Base,
    DatabaseConfig,
    DatabaseDriver,
    DatabaseSessionManager,
    create_engine,
    create_session_factory,
    get_session,
)


# Test model
class TestUser(Base):
    """Test user model for in-memory database tests."""

    __tablename__ = "test_users"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)


@pytest.fixture
def memory_db_config():
    """Create in-memory SQLite database configuration."""
    return DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)


@pytest.fixture
async def db_manager(memory_db_config):
    """Create database session manager with in-memory database."""
    manager = DatabaseSessionManager(memory_db_config)

    # Create tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield manager

    # Cleanup
    await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_engine():
    """Test engine creation."""
    config = DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)
    engine = create_engine(config)

    assert engine is not None
    assert engine.url.drivername == "sqlite+aiosqlite"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_manager_initialization(memory_db_config):
    """Test session manager initialization."""
    manager = DatabaseSessionManager(memory_db_config)

    assert manager.config == memory_db_config
    assert manager.engine is not None
    assert manager._session_factory is not None

    await manager.close()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_manager_callable(db_manager):
    """Test session manager as callable (dependency injection)."""
    # Use the manager as a dependency
    async for session in db_manager():
        assert session is not None
        # Session should be usable
        result = await session.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_session_context_manager(db_manager):
    """Test get_session as context manager."""
    async with get_session(db_manager._session_factory) as session:
        assert session is not None
        result = await session.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_crud_operations(db_manager):
    """Test basic CRUD operations with session."""
    async for session in db_manager():
        # Create
        user = TestUser(name="John Doe", email="john@example.com")
        session.add(user)
        await session.commit()
        await session.refresh(user)

        assert user.id is not None
        assert user.name == "John Doe"

        # Read
        stmt = select(TestUser).where(TestUser.email == "john@example.com")
        result = await session.execute(stmt)
        fetched_user = result.scalar_one_or_none()

        assert fetched_user is not None
        assert fetched_user.id == user.id
        assert fetched_user.name == "John Doe"

        # Update
        fetched_user.name = "Jane Doe"
        await session.commit()
        await session.refresh(fetched_user)

        assert fetched_user.name == "Jane Doe"

        # Delete
        await session.delete(fetched_user)
        await session.commit()

        stmt = select(TestUser).where(TestUser.email == "john@example.com")
        result = await session.execute(stmt)
        deleted_user = result.scalar_one_or_none()

        assert deleted_user is None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_rollback_on_error(db_manager):
    """Test session rollback on error."""
    async for session in db_manager():
        # Create first user
        user1 = TestUser(name="User 1", email="user1@example.com")
        session.add(user1)
        await session.commit()

        # Try to create duplicate email (should fail)
        try:
            user2 = TestUser(name="User 2", email="user1@example.com")
            session.add(user2)
            await session.commit()
            assert False, "Should have raised an error"
        except Exception:
            await session.rollback()

        # Verify first user still exists
        stmt = select(TestUser).where(TestUser.email == "user1@example.com")
        result = await session.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "User 1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_multiple_sessions_isolated(db_manager):
    """Test that multiple sessions are isolated."""
    # Create user in first session
    async for session1 in db_manager():
        user = TestUser(name="User A", email="usera@example.com")
        session1.add(user)
        await session1.commit()
        break

    # Read from second session
    async for session2 in db_manager():
        stmt = select(TestUser).where(TestUser.email == "usera@example.com")
        result = await session2.execute(stmt)
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.name == "User A"
        break


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_factory():
    """Test create_session_factory function."""
    config = DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)
    engine = create_engine(config)
    session_factory = create_session_factory(engine)

    assert session_factory is not None

    # Test using the factory
    async with get_session(session_factory) as session:
        result = await session.execute(select(1))
        assert result.scalar() == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_session_manager_close(memory_db_config):
    """Test session manager cleanup."""
    manager = DatabaseSessionManager(memory_db_config)

    # Manager should work before close
    async for session in manager():
        result = await session.execute(select(1))
        assert result.scalar() == 1
        break

    # Close the manager
    await manager.close()

    # Engine should be disposed
    # (We can't easily test this without implementation details)
