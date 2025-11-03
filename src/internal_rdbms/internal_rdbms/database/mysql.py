"""
MySQL database connection manager.

Provides async MySQL connection management with aiomysql.
"""

from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from .config import DatabaseConfig
from .db import Database


class MySQLDatabase(Database):
    """
    MySQL database connection manager.

    Uses aiomysql driver for async MySQL connections.

    Example:
        from internal_rdbms import MySQLDatabase, DatabaseConfig

        config = DatabaseConfig(
            driver="mysql+aiomysql",
            host="localhost",
            port=3306,
            user="root",
            password="secret",
            name="myapp",
            pool_size=10,
            echo=True
        )

        db = MySQLDatabase(config)

        async with db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

        await db.dispose()
    """

    def __init__(self, config: DatabaseConfig) -> None:
        """
        Initialize MySQL database.

        Args:
            config: Database configuration

        Example:
            config = DatabaseConfig(
                driver="mysql+aiomysql",
                host="db.example.com",
                port=3306,
                user="app_user",
                password="secret",
                name="production_db"
            )
            db = MySQLDatabase(config)
        """
        # Set default MySQL-specific connect_args if not provided
        if "charset" not in config.connect_args:
            config.connect_args.setdefault("charset", "utf8mb4")
        if "autocommit" not in config.connect_args:
            config.connect_args.setdefault("autocommit", False)

        super().__init__(config)

    def _create_engine(self) -> AsyncEngine:
        """
        Create MySQL async engine.

        Returns:
            AsyncEngine configured for MySQL with aiomysql

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
