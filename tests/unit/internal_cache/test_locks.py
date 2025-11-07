"""
Unit tests for distributed locks.

Tests DistributedLock and with_lock decorator.
"""

import pytest
import uuid
from internal_cache.locks import DistributedLock, with_lock
from internal_cache import RedisClient, RedisConfig


class TestDistributedLock:
    """Test DistributedLock."""

    def test_init(self):
        """Test lock initialization."""
        client = RedisClient()
        lock = DistributedLock(client, "test_lock", timeout=30, auto_renewal=True)

        assert lock.client == client
        assert lock.lock_name == "lock:test_lock"
        assert lock.timeout == 30
        assert lock.auto_renewal is True
        assert isinstance(lock._lock_value, str)
        # UUID validation
        try:
            uuid.UUID(lock._lock_value)
            valid_uuid = True
        except ValueError:
            valid_uuid = False
        assert valid_uuid
        assert lock._renewal_task is None

    def test_init_defaults(self):
        """Test lock initialization with defaults."""
        client = RedisClient()
        lock = DistributedLock(client, "default_lock")

        assert lock.lock_name == "lock:default_lock"
        assert lock.timeout == 10
        assert lock.auto_renewal is False

    def test_lock_name_prefix(self):
        """Test that lock name gets lock: prefix."""
        client = RedisClient()
        lock = DistributedLock(client, "my_resource")
        assert lock.lock_name == "lock:my_resource"
        assert lock.lock_name.startswith("lock:")
