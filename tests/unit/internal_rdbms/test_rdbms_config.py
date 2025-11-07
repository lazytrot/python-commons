"""
Unit tests for internal_rdbms configuration.

Tests DatabaseConfig URL construction and validation.
"""

import pytest
from internal_rdbms import DatabaseConfig


class TestDatabaseConfig:
    """Test DatabaseConfig model."""

    def test_postgresql_url(self):
        """Test PostgreSQL URL construction."""
        config = DatabaseConfig(
            driver="postgresql+asyncpg",
            host="localhost",
            port=5432,
            user="testuser",
            password="testpass",
            name="testdb"
        )
        
        assert config.url == "postgresql+asyncpg://testuser:testpass@localhost:5432/testdb"

    def test_mysql_url(self):
        """Test MySQL URL construction."""
        config = DatabaseConfig(
            driver="mysql+aiomysql",
            host="db.example.com",
            port=3306,
            user="root",
            password="secret",
            name="myapp"
        )
        
        assert config.url == "mysql+aiomysql://root:secret@db.example.com:3306/myapp"

    def test_sqlite_file_url(self):
        """Test SQLite file URL construction."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name="myapp.db"
        )
        
        assert config.url == "sqlite+aiosqlite:///./myapp.db"

    def test_sqlite_memory_url(self):
        """Test SQLite in-memory URL construction."""
        config = DatabaseConfig(
            driver="sqlite+aiosqlite",
            name=":memory:"
        )
        
        assert config.url == "sqlite+aiosqlite:///:memory:"

    def test_url_without_credentials(self):
        """Test URL construction without credentials."""
        config = DatabaseConfig(
            driver="postgresql+asyncpg",
            host="localhost",
            name="testdb"
        )
        
        # Should have default port
        assert "localhost:5432" in config.url or "localhost:" in config.url

    def test_default_pool_settings(self):
        """Test default pool settings."""
        config = DatabaseConfig()
        
        assert config.pool_size == 5
        assert config.max_overflow == 10
        assert config.pool_timeout == 30.0
        assert config.pool_recycle == 1800

    def test_custom_pool_settings(self):
        """Test custom pool settings."""
        config = DatabaseConfig(
            pool_size=20,
            max_overflow=30,
            pool_timeout=60.0,
            pool_recycle=3600
        )
        
        assert config.pool_size == 20
        assert config.max_overflow == 30
        assert config.pool_timeout == 60.0
        assert config.pool_recycle == 3600

    def test_connect_args(self):
        """Test custom connect_args."""
        config = DatabaseConfig(
            connect_args={"ssl": True, "timeout": 10}
        )
        
        assert config.connect_args == {"ssl": True, "timeout": 10}

    def test_echo_setting(self):
        """Test echo SQL setting."""
        config_echo = DatabaseConfig(echo=True)
        config_no_echo = DatabaseConfig(echo=False)
        
        assert config_echo.echo is True
        assert config_no_echo.echo is False
