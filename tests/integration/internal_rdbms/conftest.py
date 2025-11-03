"""Fixtures for internal_rdbms integration tests."""

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from testcontainers.mysql import MySqlContainer

from internal_rdbms import DatabaseConfig, PostgresDatabase, MySQLDatabase, SQLiteMemDatabase
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import Column, Integer, String


# Test model
class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(100))


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture
def postgres_config(postgres_container):
    """PostgreSQL configuration."""
    return DatabaseConfig(
        driver="postgresql+asyncpg",
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
    )


@pytest.fixture(scope="session")
def mysql_container():
    """Start MySQL container."""
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql


@pytest.fixture
def mysql_config(mysql_container):
    """MySQL configuration."""
    return DatabaseConfig(
        driver="mysql+aiomysql",
        host=mysql_container.get_container_host_ip(),
        port=int(mysql_container.get_exposed_port(3306)),
        user=mysql_container.username,
        password=mysql_container.password,
        name=mysql_container.dbname,
    )


@pytest.fixture
def sqlite_mem_config():
    """SQLite in-memory configuration."""
    return DatabaseConfig(
        driver="sqlite+aiosqlite",
        name=":memory:",
    )


@pytest_asyncio.fixture
async def postgres_db(postgres_config):
    """PostgreSQL database instance."""
    db = PostgresDatabase(postgres_config)
    
    # Create tables
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    # Cleanup
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await db.dispose()


@pytest_asyncio.fixture
async def mysql_db(mysql_config):
    """MySQL database instance."""
    db = MySQLDatabase(mysql_config)
    
    # Create tables
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    # Cleanup
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await db.dispose()


@pytest_asyncio.fixture
async def sqlite_db(sqlite_mem_config):
    """SQLite in-memory database instance."""
    db = SQLiteMemDatabase(sqlite_mem_config)
    
    # Create tables
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield db
    
    await db.dispose()
