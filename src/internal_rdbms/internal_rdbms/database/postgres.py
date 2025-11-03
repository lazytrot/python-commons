"""
PostgreSQL database connection manager.

Provides async PostgreSQL connection management with asyncpg.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .config import DatabaseConfig
from .db import Database


class PostgresDatabase(Database):
    """
    PostgreSQL database connection manager.

    Uses asyncpg driver for high-performance async PostgreSQL connections.

    Example:
        from internal_rdbms import PostgresDatabase, DatabaseConfig

        config = DatabaseConfig(
            driver="postgresql+asyncpg",
            host="localhost",
            port=5432,
            user="postgres",
            password="secret",
            name="myapp",
            pool_size=20,
            echo=False
        )

        db = PostgresDatabase(config)

        async with db.session() as session:
            result = await session.execute(
                select(User).where(User.email == "user@example.com")
            )
            user = result.scalar_one_or_none()

        await db.dispose()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize PostgreSQL database.

        Args:
            config: Database configuration

        Example:
            config = DatabaseConfig(
                driver="postgresql+asyncpg",
                host="db.example.com",
                port=5432,
                user="app_user",
                password="secret",
                name="production_db",
                pool_size=25
            )
            db = PostgresDatabase(config)
        """
        # Set default PostgreSQL-specific connect_args if not provided
        if "server_settings" not in config.connect_args:
            config.connect_args.setdefault("server_settings", {
                "application_name": "internal_rdbms"
            })

        super().__init__(config)

    def _create_engine(self) -> AsyncEngine:
        """
        Create PostgreSQL async engine.

        Returns:
            AsyncEngine configured for PostgreSQL with asyncpg

        Example:
            # Called automatically during initialization
            # Uses config.url to build connection string
            # Applies pool settings from config
        """
        return create_async_engine(
            self.settings.url,
            echo=self.settings.echo,
            pool_size=self.settings.pool_size,
            max_overflow=self.settings.max_overflow,
            pool_timeout=self.settings.pool_timeout,
            pool_recycle=self.settings.pool_recycle,
            pool_pre_ping=True,  # Enable connection health checks
            connect_args=self.settings.connect_args,
        )
