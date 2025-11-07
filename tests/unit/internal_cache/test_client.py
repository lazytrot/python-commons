"""
Unit tests for Redis client.

Tests RedisClient and RedisConfig.
"""

import pytest
import json
from internal_cache import RedisClient, RedisConfig


class TestRedisConfig:
    """Test RedisConfig dataclass."""

    def test_default_config(self):
        """Test default configuration."""
        config = RedisConfig()
        assert config.host == "localhost"
        assert config.port == 6379
        assert config.db == 0
        assert config.password is None
        assert config.username is None
        assert config.ssl is False
        assert config.socket_timeout == 5.0
        assert config.socket_connect_timeout == 5.0
        assert config.max_connections == 50
        assert config.decode_responses is True
        assert config.key_prefix == ""

    def test_custom_config(self):
        """Test custom configuration."""
        config = RedisConfig(
            host="redis.example.com",
            port=6380,
            db=1,
            password="secret",
            username="user",
            ssl=True,
            socket_timeout=10.0,
            socket_connect_timeout=3.0,
            max_connections=100,
            decode_responses=False,
            key_prefix="myapp:"
        )
        assert config.host == "redis.example.com"
        assert config.port == 6380
        assert config.db == 1
        assert config.password == "secret"
        assert config.username == "user"
        assert config.ssl is True
        assert config.socket_timeout == 10.0
        assert config.socket_connect_timeout == 3.0
        assert config.max_connections == 100
        assert config.decode_responses is False
        assert config.key_prefix == "myapp:"


class TestRedisClient:
    """Test RedisClient."""

    def test_init_default_config(self):
        """Test initialization with default config."""
        client = RedisClient()
        assert isinstance(client.config, RedisConfig)
        assert client.config.host == "localhost"
        assert client._client is None

    def test_init_custom_config(self):
        """Test initialization with custom config."""
        config = RedisConfig(host="custom.redis.com", port=6380)
        client = RedisClient(config)
        assert client.config.host == "custom.redis.com"
        assert client.config.port == 6380

    def test_get_key_without_prefix(self):
        """Test _get_key without prefix."""
        client = RedisClient()
        assert client._get_key("test:key") == "test:key"

    def test_get_key_with_prefix(self):
        """Test _get_key with prefix."""
        config = RedisConfig(key_prefix="app:")
        client = RedisClient(config)
        assert client._get_key("test:key") == "app:test:key"

    def test_client_property_not_connected(self):
        """Test client property raises error when not connected."""
        client = RedisClient()
        with pytest.raises(RuntimeError, match="Redis client not connected"):
            _ = client.client
