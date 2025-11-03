"""Tests for Redis configuration."""

import pytest
from internal_cache import RedisConfig


@pytest.mark.unit
def test_redis_config_defaults():
    """Test Redis configuration with default values."""
    config = RedisConfig()

    assert config.host == "localhost"
    assert config.port == 6379
    assert config.db == 0
    assert config.password is None
    assert config.ssl is False
    assert config.socket_timeout == 5.0
    assert config.socket_connect_timeout == 5.0
    assert config.max_connections == 50


@pytest.mark.unit
def test_redis_config_custom_values():
    """Test Redis configuration with custom values."""
    config = RedisConfig(
        host="redis.example.com",
        port=6380,
        db=2,
        password="secret",
        ssl=True,
        socket_timeout=10.0,
        socket_connect_timeout=15.0,
        max_connections=100,
    )

    assert config.host == "redis.example.com"
    assert config.port == 6380
    assert config.db == 2
    assert config.password == "secret"
    assert config.ssl is True
    assert config.socket_timeout == 10.0
    assert config.socket_connect_timeout == 15.0
    assert config.max_connections == 100


@pytest.mark.unit
def test_redis_config_url_generation_no_auth():
    """Test Redis URL generation without authentication."""
    config = RedisConfig(host="localhost", port=6379, db=0)

    url = config.url
    assert url == "redis://localhost:6379/0"


@pytest.mark.unit
def test_redis_config_url_generation_with_password():
    """Test Redis URL generation with password."""
    config = RedisConfig(
        host="localhost",
        port=6379,
        db=0,
        password="mypassword",
    )

    url = config.url
    assert url == "redis://:mypassword@localhost:6379/0"


@pytest.mark.unit
def test_redis_config_url_generation_with_ssl():
    """Test Redis URL generation with SSL."""
    config = RedisConfig(
        host="secure.redis.com",
        port=6380,
        db=1,
        password="secret",
        ssl=True,
    )

    url = config.url
    assert url == "rediss://:secret@secure.redis.com:6380/1"


@pytest.mark.unit
def test_redis_config_url_generation_ssl_no_password():
    """Test Redis URL generation with SSL but no password."""
    config = RedisConfig(
        host="secure.redis.com",
        port=6380,
        db=0,
        ssl=True,
    )

    url = config.url
    assert url == "rediss://secure.redis.com:6380/0"


@pytest.mark.unit
def test_redis_config_password_not_in_repr():
    """Test that password is not exposed in repr."""
    config = RedisConfig(password="supersecret")

    # Password field should have repr=False
    assert "supersecret" not in str(config)


@pytest.mark.unit
def test_redis_config_different_databases():
    """Test Redis configuration for different databases."""
    for db in range(16):  # Redis typically has 16 databases
        config = RedisConfig(db=db)
        assert config.db == db
        assert config.url.endswith(f"/{db}")


@pytest.mark.unit
def test_redis_config_connection_pool_settings():
    """Test Redis connection pool settings."""
    config = RedisConfig(
        max_connections=200,
        socket_timeout=30.0,
        socket_connect_timeout=10.0,
    )

    assert config.max_connections == 200
    assert config.socket_timeout == 30.0
    assert config.socket_connect_timeout == 10.0


@pytest.mark.unit
def test_redis_config_decode_responses_default():
    """Test Redis decode_responses default value."""
    config = RedisConfig()

    assert config.decode_responses is True


@pytest.mark.unit
def test_redis_config_decode_responses_disabled():
    """Test Redis with decode_responses disabled."""
    config = RedisConfig(decode_responses=False)

    assert config.decode_responses is False
