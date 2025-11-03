"""Tests for database configuration."""

import pytest
from internal_rdbms import DatabaseConfig, DatabaseDriver


@pytest.mark.unit
def test_database_config_postgresql():
    """Test PostgreSQL database configuration."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        port=5432,
        user="testuser",
        password="testpass",
        name="testdb",
    )

    assert config.driver == DatabaseDriver.POSTGRESQL
    assert config.host == "localhost"
    assert config.port == 5432
    assert config.user == "testuser"
    assert config.password == "testpass"
    assert config.name == "testdb"
    assert config.url == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"


@pytest.mark.unit
def test_database_config_postgresql_no_password():
    """Test PostgreSQL configuration without password."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        port=5432,
        user="testuser",
        name="testdb",
    )

    assert config.url == "postgresql+asyncpg://testuser@localhost:5432/testdb"


@pytest.mark.unit
def test_database_config_postgresql_defaults():
    """Test PostgreSQL with default port."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="postgres",
        name="mydb",
    )

    # Default port should be 5432
    assert "localhost:5432" in config.url


@pytest.mark.unit
def test_database_config_sqlite_memory():
    """Test SQLite in-memory database configuration."""
    config = DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)

    assert config.driver == DatabaseDriver.SQLITE_MEMORY
    assert config.url == "sqlite+aiosqlite:///:memory:"


@pytest.mark.unit
def test_database_config_sqlite_file():
    """Test SQLite file database configuration."""
    config = DatabaseConfig(
        driver=DatabaseDriver.SQLITE,
        name="test.db",
    )

    assert config.driver == DatabaseDriver.SQLITE
    assert config.url == "sqlite+aiosqlite:///./test.db"


@pytest.mark.unit
def test_database_config_sqlite_default_name():
    """Test SQLite with default database name."""
    config = DatabaseConfig(driver=DatabaseDriver.SQLITE)

    assert "database.db" in config.url


@pytest.mark.unit
def test_database_config_pool_settings():
    """Test database pool configuration."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="test",
        name="test",
        pool_size=20,
        max_overflow=40,
        pool_timeout=60.0,
        pool_recycle=7200,
    )

    assert config.pool_size == 20
    assert config.max_overflow == 40
    assert config.pool_timeout == 60.0
    assert config.pool_recycle == 7200


@pytest.mark.unit
def test_database_config_pool_defaults():
    """Test database pool default values."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="test",
        name="test",
    )

    assert config.pool_size == 10
    assert config.max_overflow == 20
    assert config.pool_timeout == 30.0
    assert config.pool_recycle == 3600
    assert config.pool_pre_ping is True
    assert config.echo is False
    assert config.echo_pool is False


@pytest.mark.unit
def test_database_config_echo_settings():
    """Test database echo configuration."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="test",
        name="test",
        echo=True,
        echo_pool=True,
    )

    assert config.echo is True
    assert config.echo_pool is True


@pytest.mark.unit
def test_database_config_connect_args():
    """Test database connect_args configuration."""
    connect_args = {"ssl": True, "timeout": 10}
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="test",
        name="test",
        connect_args=connect_args,
    )

    assert config.connect_args == connect_args


@pytest.mark.unit
def test_database_config_password_not_in_repr():
    """Test that password is not exposed in repr."""
    config = DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host="localhost",
        user="test",
        password="secret123",
        name="test",
    )

    # Password field should have repr=False
    assert "secret123" not in str(config)


@pytest.mark.unit
def test_database_driver_values():
    """Test DatabaseDriver enum values."""
    assert DatabaseDriver.POSTGRESQL.value == "postgresql+asyncpg"
    assert DatabaseDriver.SQLITE.value == "sqlite+aiosqlite"
    assert DatabaseDriver.SQLITE_MEMORY.value == "sqlite+aiosqlite:///:memory:"
