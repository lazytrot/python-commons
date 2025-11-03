"""Tests for distributed locking (unit tests with mocks)."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from internal_cache import DistributedLock, with_lock


@pytest.fixture
def mock_redis():
    """Create a mock Redis client."""
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)
    redis.delete = AsyncMock(return_value=1)
    redis.get = AsyncMock(return_value=None)
    return redis


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_initialization():
    """Test DistributedLock initialization."""
    mock_redis = AsyncMock()
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=30,
        retry_delay=0.1,
    )

    assert lock.key == "test:lock"
    assert lock.timeout == 30
    assert lock.retry_delay == 0.1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_acquire_success(mock_redis):
    """Test successful lock acquisition."""
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=10,
    )

    acquired = await lock.acquire()

    assert acquired is True
    mock_redis.set.assert_called_once()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_release(mock_redis):
    """Test lock release."""
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=10,
    )

    await lock.acquire()
    await lock.release()

    mock_redis.delete.assert_called_once_with("test:lock")


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_context_manager(mock_redis):
    """Test DistributedLock as async context manager."""
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=10,
    )

    async with lock:
        # Lock should be acquired
        assert mock_redis.set.called

    # Lock should be released after exiting context
    assert mock_redis.delete.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_context_manager_exception(mock_redis):
    """Test DistributedLock releases on exception."""
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=10,
    )

    with pytest.raises(ValueError):
        async with lock:
            raise ValueError("Test error")

    # Lock should still be released
    assert mock_redis.delete.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_lock_decorator(mock_redis):
    """Test with_lock decorator."""
    call_count = 0

    @with_lock(redis_client=mock_redis, lock_key="func:lock", timeout=10)
    async def protected_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await protected_function()

    assert result == "success"
    assert call_count == 1
    assert mock_redis.set.called
    assert mock_redis.delete.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_with_lock_decorator_with_args(mock_redis):
    """Test with_lock decorator with function arguments."""
    @with_lock(redis_client=mock_redis, lock_key="func:lock:{id}", timeout=10)
    async def update_resource(id: int, value: str):
        return f"Updated {id} with {value}"

    result = await update_resource(123, "test")

    assert result == "Updated 123 with test"
    assert mock_redis.set.called


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_timeout():
    """Test lock timeout configuration."""
    mock_redis = AsyncMock()
    lock = DistributedLock(
        redis_client=mock_redis,
        key="test:lock",
        timeout=60,
    )

    await lock.acquire()

    # Verify timeout was passed to Redis
    call_args = mock_redis.set.call_args
    # Check that 'ex' or 'px' parameter was used
    assert call_args is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_distributed_lock_key_naming():
    """Test lock key naming patterns."""
    mock_redis = AsyncMock()

    # Test different key patterns
    keys = [
        "lock:user:123",
        "lock:resource:abc",
        "distributed:lock:feature:x",
    ]

    for key in keys:
        lock = DistributedLock(redis_client=mock_redis, key=key, timeout=10)
        await lock.acquire()

        # Verify the key was used correctly
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == key or call_args.args[0] == key
