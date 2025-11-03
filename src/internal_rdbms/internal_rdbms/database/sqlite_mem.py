"""
SQLite in-memory database connection manager.

Provides async SQLite in-memory connection management with aiosqlite.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from .config import DatabaseConfig
from .db import Database


class SQLiteMemDatabase(Database):
    """
    SQLite in-memory database connection manager.

    Uses aiosqlite driver for async SQLite in-memory connections.
    Perfect for testing - fast, isolated, and ephemeral.

    IMPORTANT: Uses StaticPool to ensure single connection is reused,
    which is critical for in-memory databases (otherwise each connection
    would see a different empty database).

    Example:
        from internal_rdbms import SQLiteMemDatabase, DatabaseConfig

        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:",
            echo=True
        )

        db = SQLiteMemDatabase(config)

        # Create tables
        async with db._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        # Use database
        async with db.session() as session:
            user = User(name="Test", email="test@example.com")
            session.add(user)

        await db.dispose()
        # Database is gone after disposal (in-memory only)
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize SQLite in-memory database.

        Args:
            config: Database configuration

        Example:
            config = DatabaseConfig(
                driver="sqlite+aiosqlite",
                name=":memory:",
                echo=False
            )
            db = SQLiteMemDatabase(config)
        """
        # Force in-memory database
        if config.name != ":memory:":
            config.name = ":memory:"

        # Set default SQLite-specific connect_args if not provided
        if "check_same_thread" not in config.connect_args:
            config.connect_args.setdefault("check_same_thread", False)

        super().__init__(config)

    def _create_engine(self) -> AsyncEngine:
        """
        Create SQLite in-memory async engine.

        Uses StaticPool to ensure a single connection is reused across all sessions.
        This is critical for in-memory databases - without it, each connection would
        create a new empty database.

        Returns:
            AsyncEngine configured for SQLite in-memory with aiosqlite

        Example:
            # Called automatically during initialization
            # Creates engine pointing to in-memory database
            # Uses StaticPool for connection reuse
        """
        return create_async_engine(
            self.settings.url,
            echo=self.settings.echo,
            poolclass=StaticPool,  # Critical: reuse single connection
            connect_args=self.settings.connect_args,
        )
