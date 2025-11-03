"""
SQLite file-based database connection manager.

Provides async SQLite connection management with aiosqlite.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import NullPool

from .config import DatabaseConfig
from .db import Database


class SQLiteDatabase(Database):
    """
    SQLite file-based database connection manager.

    Uses aiosqlite driver for async SQLite connections.
    Suitable for development, testing, and lightweight production use cases.

    Example:
        from internal_rdbms import SQLiteDatabase, DatabaseConfig

        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name="myapp.db",  # Creates ./myapp.db
            echo=True
        )

        db = SQLiteDatabase(config)

        async with db.session() as session:
            user = User(name="John", email="john@example.com")
            session.add(user)
            # Automatically commits

        await db.dispose()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize SQLite file-based database.

        Args:
            config: Database configuration

        Example:
            config = DatabaseConfig(
                driver="sqlite+aiosqlite",
                name="data/app.db",
                echo=False
            )
            db = SQLiteDatabase(config)
        """
        # Set default SQLite-specific connect_args if not provided
        if "check_same_thread" not in config.connect_args:
            config.connect_args.setdefault("check_same_thread", False)

        super().__init__(config)

    def _create_engine(self) -> AsyncEngine:
        """
        Create SQLite file-based async engine.

        Uses NullPool since SQLite doesn't support connection pooling effectively.

        Returns:
            AsyncEngine configured for SQLite with aiosqlite

        Example:
            # Called automatically during initialization
            # Creates engine pointing to file: ./database.db
            # No connection pooling (uses NullPool)
        """
        return create_async_engine(
            self.settings.url,
            echo=self.settings.echo,
            poolclass=NullPool,  # SQLite doesn't benefit from pooling
            connect_args=self.settings.connect_args,
        )
