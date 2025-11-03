"""
Abstract database connection manager.

Provides base class for database implementations.
"""

from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from .config import DatabaseConfig


class Database(ABC):
    """
    Abstract database connection manager.

    Provides common functionality for database connections with SQLAlchemy.
    Subclasses must implement _create_engine() for specific database types.

    Example:
        class MyDatabase(Database):
            def _create_engine(self) -> AsyncEngine:
                return create_async_engine(
                    self.settings.url,
                    echo=self.settings.echo,
                    pool_size=self.settings.pool_size,
                )

        config = DatabaseConfig(driver="mysql+aiomysql", host="localhost", name="mydb")
        db = MyDatabase(config)

        async with db.session() as session:
            result = await session.execute(select(User))
            users = result.scalars().all()

        await db.dispose()
    """

    def __init__(self, settings: DatabaseConfig) -> None:
        """
        Initialize database connection manager.

        Args:
            settings: Database configuration

        Example:
            config = DatabaseConfig(
                driver="postgresql+asyncpg",
                host="localhost",
                port=5432,
                user="myuser",
                password="mypass",
                name="mydb"
            )
            db = PostgresDatabase(config)
        """
        self.settings = settings
        self._engine: AsyncEngine = self._create_engine()
        self._session_factory: async_sessionmaker[AsyncSession] = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )

    @abstractmethod
    def _create_engine(self) -> AsyncEngine:
        """
        Create database engine.

        Must be implemented by subclasses to provide database-specific engine creation.

        Returns:
            AsyncEngine instance

        Example:
            def _create_engine(self) -> AsyncEngine:
                return create_async_engine(
                    self.settings.url,
                    echo=self.settings.echo,
                    pool_size=self.settings.pool_size,
                    max_overflow=self.settings.max_overflow,
                    pool_timeout=self.settings.pool_timeout,
                    pool_recycle=self.settings.pool_recycle,
                    connect_args=self.settings.connect_args,
                )
        """
        pass

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession, None]:
        """
        Create and manage a database session.

        Provides automatic transaction handling - commits on success, rolls back on error.

        Yields:
            AsyncSession instance

        Example:
            async with db.session() as session:
                user = User(name="John", email="john@example.com")
                session.add(user)
                # Automatically commits on exit
                # Automatically rolls back on exception
        """
        session = self._session_factory()
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def dispose(self) -> None:
        """
        Dispose of the database engine and close all connections.

        Should be called during application shutdown.

        Example:
            # At application startup
            db = PostgresDatabase(config)

            # At application shutdown
            await db.dispose()
        """
        await self._engine.dispose()
