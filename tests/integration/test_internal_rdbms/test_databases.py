"""
Integration tests for internal_rdbms databases.

Tests PostgreSQL, MySQL, and SQLite with real database containers.
NO MOCKING - uses testcontainers for real databases.
"""

import pytest
from sqlalchemy import select
from tests.integration.test_internal_rdbms.conftest import User


@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.asyncio
class TestPostgresDatabase:
    """Test PostgreSQL database with real container."""

    async def test_postgres_connection(self, postgres_db):
        """Test PostgreSQL connection."""
        async with postgres_db.session() as session:
            # Simple query to verify connection
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert users == []

    async def test_postgres_insert_and_query(self, postgres_db):
        """Test inserting and querying data in PostgreSQL."""
        async with postgres_db.session() as session:
            # Insert user
            user = User(name="John Doe", email="john@example.com")
            session.add(user)
        
        # Query user
        async with postgres_db.session() as session:
            result = await session.execute(select(User).where(User.name == "John Doe"))
            found_user = result.scalar_one()
            assert found_user.name == "John Doe"
            assert found_user.email == "john@example.com"

    async def test_postgres_transaction_commit(self, postgres_db):
        """Test transaction commit in PostgreSQL."""
        async with postgres_db.session() as session:
            user = User(name="Jane Doe", email="jane@example.com")
            session.add(user)
            # Automatically commits on exit
        
        # Verify committed
        async with postgres_db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert len(users) == 1

    async def test_postgres_transaction_rollback(self, postgres_db):
        """Test transaction rollback in PostgreSQL."""
        try:
            async with postgres_db.session() as session:
                user = User(name="Test User", email="test@example.com")
                session.add(user)
                raise RuntimeError("Force rollback")
        except RuntimeError:
            pass
        
        # Verify rolled back
        async with postgres_db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert len(users) == 0


@pytest.mark.integration
@pytest.mark.mysql
@pytest.mark.asyncio
class TestMySQLDatabase:
    """Test MySQL database with real container."""

    async def test_mysql_connection(self, mysql_db):
        """Test MySQL connection."""
        async with mysql_db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert users == []

    async def test_mysql_insert_and_query(self, mysql_db):
        """Test inserting and querying data in MySQL."""
        async with mysql_db.session() as session:
            user = User(name="Alice", email="alice@example.com")
            session.add(user)
        
        async with mysql_db.session() as session:
            result = await session.execute(select(User).where(User.name == "Alice"))
            found_user = result.scalar_one()
            assert found_user.name == "Alice"
            assert found_user.email == "alice@example.com"

    async def test_mysql_transaction_commit(self, mysql_db):
        """Test transaction commit in MySQL."""
        async with mysql_db.session() as session:
            user = User(name="Bob", email="bob@example.com")
            session.add(user)
        
        async with mysql_db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert len(users) == 1


@pytest.mark.unit
@pytest.mark.asyncio
class TestSQLiteMemDatabase:
    """Test SQLite in-memory database (fast unit tests)."""

    async def test_sqlite_connection(self, sqlite_db):
        """Test SQLite in-memory connection."""
        async with sqlite_db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()
            assert users == []

    async def test_sqlite_insert_and_query(self, sqlite_db):
        """Test inserting and querying in SQLite."""
        async with sqlite_db.session() as session:
            user = User(name="Charlie", email="charlie@example.com")
            session.add(user)

        async with sqlite_db.session() as session:
            result = await session.execute(select(User).where(User.name == "Charlie"))
            found_user = result.scalar_one()
            assert found_user.name == "Charlie"

    async def test_sqlite_multiple_operations(self, sqlite_db):
        """Test multiple operations in SQLite."""
        # Insert multiple users
        async with sqlite_db.session() as session:
            users = [
                User(name=f"User{i}", email=f"user{i}@example.com")
                for i in range(10)
            ]
            for user in users:
                session.add(user)

        # Query all
        async with sqlite_db.session() as session:
            result = await session.execute(select(User))
            all_users = result.scalars().all()
            assert len(all_users) == 10


@pytest.mark.unit
@pytest.mark.asyncio
class TestSQLiteFileDatabase:
    """Test SQLite file-based database."""

    async def test_sqlite_file_with_connect_args(self):
        """Test SQLite file database with custom connect_args."""
        from internal_rdbms import SQLiteDatabase, DatabaseConfig
        import tempfile
        import os

        # Create temp database file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # Test with custom connect_args
            config = DatabaseConfig(
                driver="sqlite+aiosqlite",
                name=db_path,
                echo=False,
                connect_args={"check_same_thread": False, "timeout": 10}
            )
            db = SQLiteDatabase(config)

            # Verify engine was created
            assert db._engine is not None
            assert "check_same_thread" in db.settings.connect_args
            assert db.settings.connect_args["check_same_thread"] is False

            await db.dispose()
        finally:
            # Cleanup
            if os.path.exists(db_path):
                os.unlink(db_path)

    async def test_sqlite_file_default_connect_args(self):
        """Test SQLite sets default check_same_thread."""
        from internal_rdbms import SQLiteDatabase, DatabaseConfig
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as f:
            db_path = f.name

        try:
            # Test without connect_args - should set default
            config = DatabaseConfig(
                driver="sqlite+aiosqlite",
                name=db_path,
                echo=False
            )
            db = SQLiteDatabase(config)

            # Should have added check_same_thread=False by default
            assert "check_same_thread" in db.settings.connect_args
            assert db.settings.connect_args["check_same_thread"] is False

            await db.dispose()
        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)
