"""
Redis client wrapper with async support.

Provides high-level interface for Redis operations.
"""

import json
import logging
from typing import Any, Optional, Union
from dataclasses import dataclass

import redis.asyncio as redis
from redis.asyncio import Redis


logger = logging.getLogger(__name__)


@dataclass
class RedisConfig:
    """Configuration for Redis client."""

    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    username: Optional[str] = None
    ssl: bool = False
    socket_timeout: float = 5.0
    socket_connect_timeout: float = 5.0
    max_connections: int = 50
    decode_responses: bool = True
    key_prefix: str = ""  # Global prefix for all keys


class RedisClient:
    """
    Async Redis client wrapper.

    Provides convenient methods for common Redis operations with
    automatic JSON serialization and key prefixing.
    """

    def __init__(self, config: Optional[RedisConfig] = None):
        """
        Initialize Redis client.

        Args:
            config: Redis configuration

        Example:
            from internal_cache import RedisClient, RedisConfig

            config = RedisConfig(
                host="redis.example.com",
                password="secret",
                key_prefix="myapp:"
            )
            client = RedisClient(config)

            await client.set("user:123", {"name": "John"}, ttl=3600)
        """
        self.config = config or RedisConfig()
        self._client: Optional[Redis] = None

    async def connect(self) -> None:
        """Establish Redis connection."""
        if self._client:
            return

        # Build connection kwargs, only include ssl if True
        connection_kwargs = {
            "password": self.config.password,
            "username": self.config.username,
            "socket_timeout": self.config.socket_timeout,
            "socket_connect_timeout": self.config.socket_connect_timeout,
            "max_connections": self.config.max_connections,
            "decode_responses": self.config.decode_responses,
        }

        if self.config.ssl:
            connection_kwargs["ssl"] = True

        self._client = await redis.from_url(
            f"redis://{self.config.host}:{self.config.port}/{self.config.db}",
            **connection_kwargs
        )

        logger.info(f"Connected to Redis at {self.config.host}:{self.config.port}")

    async def close(self) -> None:
        """Close Redis connection."""
        if self._client:
            await self._client.aclose()
            self._client = None
            logger.info("Redis connection closed")

    def _get_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.config.key_prefix}{key}"

    @property
    def client(self) -> Redis:
        """Get underlying Redis client."""
        if not self._client:
            raise RuntimeError("Redis client not connected. Call connect() first.")
        return self._client

    async def get(self, key: str, default: Any = None) -> Any:
        """
        Get value from Redis.

        Automatically deserializes JSON.

        Args:
            key: Cache key
            default: Default value if key not found

        Returns:
            Cached value or default

        Example:
            value = await client.get("user:123")
        """
        try:
            value = await self.client.get(self._get_key(key))
            if value is None:
                return default

            # Try to deserialize JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Failed to get key '{key}': {e}")
            return default

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
        nx: bool = False,
        xx: bool = False,
    ) -> bool:
        """
        Set value in Redis.

        Automatically serializes to JSON.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
            nx: Only set if key doesn't exist
            xx: Only set if key exists

        Returns:
            True if set successfully

        Example:
            await client.set("user:123", {"name": "John"}, ttl=3600)
        """
        try:
            # Serialize to JSON if not a string
            if not isinstance(value, (str, bytes)):
                value = json.dumps(value)

            result = await self.client.set(
                self._get_key(key),
                value,
                ex=ttl,
                nx=nx,
                xx=xx,
            )

            return bool(result)

        except Exception as e:
            logger.error(f"Failed to set key '{key}': {e}")
            return False

    async def delete(self, *keys: str) -> int:
        """
        Delete one or more keys.

        Args:
            *keys: Keys to delete

        Returns:
            Number of keys deleted

        Example:
            count = await client.delete("user:123", "user:124")
        """
        try:
            prefixed_keys = [self._get_key(key) for key in keys]
            return await self.client.delete(*prefixed_keys)
        except Exception as e:
            logger.error(f"Failed to delete keys: {e}")
            return 0

    async def exists(self, *keys: str) -> int:
        """
        Check if keys exist.

        Args:
            *keys: Keys to check

        Returns:
            Number of existing keys

        Example:
            count = await client.exists("user:123")
        """
        try:
            prefixed_keys = [self._get_key(key) for key in keys]
            return await self.client.exists(*prefixed_keys)
        except Exception as e:
            logger.error(f"Failed to check existence: {e}")
            return 0

    async def expire(self, key: str, ttl: int) -> bool:
        """
        Set TTL on a key.

        Args:
            key: Cache key
            ttl: Time-to-live in seconds

        Returns:
            True if TTL was set

        Example:
            await client.expire("user:123", 3600)
        """
        try:
            return await self.client.expire(self._get_key(key), ttl)
        except Exception as e:
            logger.error(f"Failed to set expiry on '{key}': {e}")
            return False

    async def ttl(self, key: str) -> int:
        """
        Get remaining TTL.

        Args:
            key: Cache key

        Returns:
            TTL in seconds (-1 if no expiry, -2 if key doesn't exist)

        Example:
            seconds_left = await client.ttl("user:123")
        """
        try:
            return await self.client.ttl(self._get_key(key))
        except Exception as e:
            logger.error(f"Failed to get TTL for '{key}': {e}")
            return -2

    async def increment(self, key: str, amount: int = 1) -> int:
        """
        Increment a numeric value.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value after increment

        Example:
            views = await client.increment("page:views:123")
        """
        try:
            return await self.client.incrby(self._get_key(key), amount)
        except Exception as e:
            logger.error(f"Failed to increment '{key}': {e}")
            return 0

    async def decrement(self, key: str, amount: int = 1) -> int:
        """
        Decrement a numeric value.

        Args:
            key: Cache key
            amount: Amount to decrement by

        Returns:
            New value after decrement

        Example:
            stock = await client.decrement("product:stock:123")
        """
        try:
            return await self.client.decrby(self._get_key(key), amount)
        except Exception as e:
            logger.error(f"Failed to decrement '{key}': {e}")
            return 0

    async def scan_keys(self, pattern: str = "*", count: int = 100) -> list[str]:
        """
        Scan for keys matching a pattern.

        Args:
            pattern: Key pattern (with wildcards)
            count: Hint for batch size

        Returns:
            List of matching keys

        Example:
            user_keys = await client.scan_keys("user:*")
        """
        try:
            keys = []
            cursor = 0
            pattern_with_prefix = self._get_key(pattern)

            while True:
                cursor, batch = await self.client.scan(
                    cursor, match=pattern_with_prefix, count=count
                )
                keys.extend(batch)

                if cursor == 0:
                    break

            # Remove prefix from results
            prefix_len = len(self.config.key_prefix)
            return [key[prefix_len:] for key in keys]

        except Exception as e:
            logger.error(f"Failed to scan keys: {e}")
            return []

    async def flush_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.

        Args:
            pattern: Key pattern

        Returns:
            Number of keys deleted

        Example:
            count = await client.flush_pattern("session:*")
        """
        keys = await self.scan_keys(pattern)
        if keys:
            return await self.delete(*keys)
        return 0

    async def ping(self) -> bool:
        """
        Check if Redis is alive.

        Returns:
            True if connection is healthy

        Example:
            if await client.ping():
                print("Redis is up!")
        """
        try:
            result = await self.client.ping()
            return result
        except Exception as e:
            logger.error(f"Redis ping failed: {e}")
            return False
