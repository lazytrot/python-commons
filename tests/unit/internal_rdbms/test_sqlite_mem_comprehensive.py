"""
Comprehensive tests for SQLite in-memory database to achieve 100% coverage.

Tests all uncovered lines including initialization and engine creation.
"""

import pytest
from sqlalchemy.pool import StaticPool
from sqlalchemy.ext.asyncio import AsyncEngine

from internal_rdbms.database.config import DatabaseConfig
from internal_rdbms.database.sqlite_mem import SQLiteMemDatabase


class TestSQLiteMemDatabase:
    """Test SQLiteMemDatabase initialization and configuration."""

    def test_init_forces_memory_database(self):
        """Test that initialization forces :memory: database name."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name="some_file.db"  # Try to use file-based
        )

        db = SQLiteMemDatabase(config)

        # Should be forced to :memory:
        assert db.settings.name == ":memory:"

    def test_init_with_memory_database(self):
        """Test initialization with :memory: database."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        assert db.settings.name == ":memory:"

    def test_init_sets_check_same_thread_false(self):
        """Test that check_same_thread is set to False."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        assert "check_same_thread" in db.settings.connect_args
        assert db.settings.connect_args["check_same_thread"] is False

    def test_init_preserves_existing_connect_args(self):
        """Test that existing connect_args are preserved."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            connect_args={"timeout": 30}
        )

        db = SQLiteMemDatabase(config)

        assert db.settings.connect_args["timeout"] == 30
        assert db.settings.connect_args["check_same_thread"] is False

    def test_init_does_not_override_check_same_thread(self):
        """Test that explicitly set check_same_thread is not overridden."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            connect_args={"check_same_thread": True}
        )

        db = SQLiteMemDatabase(config)

        # Should keep the explicit value
        assert db.settings.connect_args["check_same_thread"] is True

    def test_create_engine_returns_async_engine(self):
        """Test that _create_engine returns AsyncEngine."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            echo=True
        )

        db = SQLiteMemDatabase(config)

        assert isinstance(db._engine, AsyncEngine)

    def test_create_engine_uses_static_pool(self):
        """Test that _create_engine uses StaticPool."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        # Check that StaticPool is used
        assert db._engine.pool.__class__ == StaticPool

    def test_create_engine_respects_echo(self):
        """Test that _create_engine respects echo setting."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            echo=True
        )

        db = SQLiteMemDatabase(config)

        assert db._engine.echo is True

    def test_create_engine_with_connect_args(self):
        """Test that _create_engine passes connect_args."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            connect_args={
                "check_same_thread": False,
                "timeout": 30
            }
        )

        db = SQLiteMemDatabase(config)

        # Engine should be created successfully with connect_args
        assert isinstance(db._engine, AsyncEngine)

    @pytest.mark.asyncio
    async def test_full_lifecycle(self):
        """Test full database lifecycle with SQLiteMemDatabase."""
        from sqlalchemy import Column, Integer, String
        from sqlalchemy.orm import DeclarativeBase

        # Create test base
        class Base(DeclarativeBase):
            pass

        # Create test model
        class TestModel(Base):
            __tablename__ = "test_table"
            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            echo=False
        )

        db = SQLiteMemDatabase(config)

        # Create tables
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Use database
        async with db.session() as session:
            # Add record
            record = TestModel(id=1, name="Test")
            session.add(record)
            await session.commit()

            # Query record
            result = await session.get(TestModel, 1)
            assert result is not None
            assert result.name == "Test"

        # Cleanup
        await db.dispose()

    @pytest.mark.asyncio
    async def test_multiple_sessions_share_data(self):
        """Test that multiple sessions see the same in-memory database."""
        from sqlalchemy import Column, Integer, String, select
        from sqlalchemy.orm import DeclarativeBase

        # Create test base
        class Base(DeclarativeBase):
            pass

        # Create test model
        class SharedModel(Base):
            __tablename__ = "shared_table"
            id = Column(Integer, primary_key=True)
            value = Column(String(50))

        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        # Create tables
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Session 1: Insert data
        async with db.session() as session1:
            record = SharedModel(id=1, value="shared_data")
            session1.add(record)
            await session1.commit()

        # Session 2: Read data
        async with db.session() as session2:
            stmt = select(SharedModel).where(SharedModel.id == 1)
            result = await session2.execute(stmt)
            record = result.scalar_one()
            assert record.value == "shared_data"

        await db.dispose()

    def test_url_generation(self):
        """Test that URL is correctly generated for in-memory database."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        assert db.settings.url == "sqlite+aiosqlite:///:memory:"

    @pytest.mark.asyncio
    async def test_database_is_ephemeral(self):
        """Test that database is ephemeral (data lost after disposal)."""
        from sqlalchemy import Column, Integer, String, select
        from sqlalchemy.orm import DeclarativeBase

        # Create test base
        class Base(DeclarativeBase):
            pass

        # Create test model
        class EphemeralModel(Base):
            __tablename__ = "ephemeral_table"
            id = Column(Integer, primary_key=True)
            data = Column(String(50))

        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )

        db = SQLiteMemDatabase(config)

        # Create tables and add data
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with db.session() as session:
            record = EphemeralModel(id=1, data="temp_data")
            session.add(record)
            await session.commit()

        # Dispose database
        await db.dispose()

        # Create new database instance with same config
        db2 = SQLiteMemDatabase(config)

        # Tables should not exist
        async with db2._engine.begin() as conn:
            # Need to create tables again
            await conn.run_sync(Base.metadata.create_all)

        # Data should not exist
        async with db2.session() as session:
            stmt = select(EphemeralModel)
            result = await session.execute(stmt)
            records = result.scalars().all()
            assert len(records) == 0

        await db2.dispose()
