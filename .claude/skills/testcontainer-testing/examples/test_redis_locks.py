"""
Comprehensive integration tests for distributed locks to achieve 100% coverage.

Tests all uncovered lines with real Redis testcontainers.
Uses shared session-scoped Redis container from root conftest.py for speed.
"""

import pytest
import asyncio
from internal_cache import DistributedLock, with_lock
from tests.test_utils import wait_for_condition, wait_for_lock_renewal

# Note: redis_client fixture is provided by tests/conftest.py with session-scoped Redis container


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_acquire_with_auto_renewal(redis_client):
    """Test lock acquisition with auto-renewal enabled."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:auto_renew",
        timeout=2,
        auto_renewal=True,
    )

    # Acquire lock with auto-renewal
    acquired = await lock.acquire()
    assert acquired is True
    assert lock._renewal_task is not None

    # Wait for renewal to happen (condition-based, not time-based)
    initial_ttl = await redis_client.ttl("lock:test:auto_renew")
    await wait_for_lock_renewal(redis_client, "lock:test:auto_renew", initial_ttl)

    # Lock should still exist
    exists = await redis_client.exists("lock:test:auto_renew")
    assert exists > 0

    # Release lock
    released = await lock.release()
    assert released is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_acquire_non_blocking_when_locked(redis_client):
    """Test non-blocking acquire returns False when lock is held."""
    lock1 = DistributedLock(
        client=redis_client,
        lock_name="test:non_blocking",
        timeout=10,
    )

    lock2 = DistributedLock(
        client=redis_client,
        lock_name="test:non_blocking",
        timeout=10,
    )

    # First lock acquires
    acquired1 = await lock1.acquire()
    assert acquired1 is True

    # Second lock fails non-blocking
    acquired2 = await lock2.acquire(blocking=False)
    assert acquired2 is False

    # Release first lock
    await lock1.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_acquire_blocking_with_timeout_expires(redis_client):
    """Test blocking acquire with timeout that expires."""
    lock1 = DistributedLock(
        client=redis_client,
        lock_name="test:blocking_timeout",
        timeout=10,
    )

    lock2 = DistributedLock(
        client=redis_client,
        lock_name="test:blocking_timeout",
        timeout=10,
    )

    # First lock acquires
    await lock1.acquire()

    # Second lock waits with timeout and fails
    acquired2 = await lock2.acquire(blocking=True, timeout=0.5)
    assert acquired2 is False

    # Release first lock
    await lock1.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_acquire_blocking_with_timeout_succeeds(redis_client):
    """Test blocking acquire with timeout that succeeds after wait."""
    lock1 = DistributedLock(
        client=redis_client,
        lock_name="test:blocking_success",
        timeout=1,
    )

    lock2 = DistributedLock(
        client=redis_client,
        lock_name="test:blocking_success",
        timeout=10,
    )

    # First lock acquires
    await lock1.acquire()

    # Release first lock after short delay
    async def release_after_delay():
        await asyncio.sleep(0.3)  # Legitimate: testing blocking timeout behavior
        await lock1.release()

    asyncio.create_task(release_after_delay())

    # Second lock waits and succeeds
    acquired2 = await lock2.acquire(blocking=True, timeout=2.0)
    assert acquired2 is True

    await lock2.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_release_with_auto_renewal_cancellation(redis_client):
    """Test lock release properly cancels auto-renewal task."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:renewal_cancel",
        timeout=5,
        auto_renewal=True,
    )

    await lock.acquire()
    assert lock._renewal_task is not None

    # Release should cancel renewal task
    await lock.release()
    assert lock._renewal_task is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_release_not_owner(redis_client):
    """Test lock release when not owner returns False."""
    lock1 = DistributedLock(
        client=redis_client,
        lock_name="test:not_owner",
        timeout=10,
    )

    lock2 = DistributedLock(
        client=redis_client,
        lock_name="test:not_owner",
        timeout=10,
    )

    # Lock1 acquires
    await lock1.acquire()

    # Lock2 tries to release (but doesn't own it)
    released = await lock2.release()
    assert released is False

    # Lock1 can still release
    released1 = await lock1.release()
    assert released1 is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_release_with_redis_error(redis_client):
    """Test lock release handles Redis errors gracefully."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:redis_error",
        timeout=10,
    )

    await lock.acquire()

    # Simulate Redis error by closing connection
    await redis_client.close()

    # Release should handle error and return False
    released = await lock.release()
    assert released is False

    # Reconnect for cleanup
    await redis_client.connect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_renew_loop_renews_successfully(redis_client):
    """Test auto-renewal loop successfully renews lock."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:renew_loop",
        timeout=1,  # Short timeout for fast testing
        auto_renewal=True,
    )

    await lock.acquire()

    # Get initial TTL
    initial_ttl = await redis_client.ttl("lock:test:renew_loop")

    # Wait for renewal to happen (condition-based)
    await wait_for_lock_renewal(redis_client, "lock:test:renew_loop", initial_ttl)

    # TTL should be refreshed
    refreshed_ttl = await redis_client.ttl("lock:test:renew_loop")
    assert refreshed_ttl >= initial_ttl - 1  # Account for timing

    await lock.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_renew_loop_detects_lost_ownership(redis_client):
    """Test auto-renewal loop detects when lock ownership is lost."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:lost_ownership",
        timeout=1,
        auto_renewal=True,
    )

    await lock.acquire()

    # Manually delete the lock to simulate lost ownership
    await redis_client.delete("lock:test:lost_ownership")

    # Wait for renewal task to detect lost ownership (condition-based)
    await wait_for_condition(
        lambda: lock._renewal_task is None or lock._renewal_task.done(),
        "renewal task to stop after ownership lost",
        timeout_ms=2000
    )

    # Lock should not exist
    exists = await redis_client.exists("lock:test:lost_ownership")
    assert exists == 0

    # Cleanup
    await lock.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_renew_loop_cancelled(redis_client):
    """Test auto-renewal loop handles cancellation properly."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:renewal_cancelled",
        timeout=2,
        auto_renewal=True,
    )

    await lock.acquire()
    renewal_task = lock._renewal_task

    # Cancel the renewal task
    renewal_task.cancel()

    # Wait for task to be cancelled (condition-based)
    await wait_for_condition(
        lambda: renewal_task.cancelled(),
        "renewal task to be cancelled",
        timeout_ms=500
    )

    # Task should be cancelled
    assert renewal_task.cancelled()

    # Release should handle cancelled task
    await lock.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_context_manager_acquire_failure(redis_client):
    """Test context manager raises error when acquire fails."""
    lock1 = DistributedLock(
        client=redis_client,
        lock_name="test:ctx_fail",
        timeout=10,
    )

    lock2 = DistributedLock(
        client=redis_client,
        lock_name="test:ctx_fail",
        timeout=10,
    )

    # First lock acquires
    await lock1.acquire()

    # Second lock's acquire should fail, and context manager should raise RuntimeError
    # We need to manually acquire non-blocking
    acquired = await lock2.acquire(blocking=False)
    assert acquired is False

    # Now test context manager with blocking that will fail
    lock3 = DistributedLock(
        client=redis_client,
        lock_name="test:ctx_fail",
        timeout=10,
    )

    # Mock acquire to return False
    original_acquire = lock3.acquire

    async def mock_acquire(blocking=True, timeout=None):
        return False

    lock3.acquire = mock_acquire

    # Context manager should raise RuntimeError when acquire returns False
    with pytest.raises(RuntimeError, match="Failed to acquire lock"):
        async with lock3:
            pass

    await lock1.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_lock_context_manager_returns_false_on_exit(redis_client):
    """Test context manager __aexit__ returns False."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:ctx_exit",
        timeout=10,
    )

    # Test that __aexit__ returns False (doesn't suppress exceptions)
    async with lock:
        pass

    # Lock should be released
    exists = await redis_client.exists("lock:test:ctx_exit")
    assert exists == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_lock_decorator_success(redis_client):
    """Test with_lock decorator successfully acquires and releases lock."""
    call_count = 0

    @with_lock(redis_client, "test:decorator", timeout=10)
    async def decorated_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await decorated_function()

    assert result == "success"
    assert call_count == 1

    # Lock should be released
    exists = await redis_client.exists("lock:test:decorator")
    assert exists == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_lock_decorator_non_blocking_failure(redis_client):
    """Test with_lock decorator with non-blocking fails when lock is held."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:decorator_fail",
        timeout=10,
    )

    # Acquire lock manually
    await lock.acquire()

    @with_lock(redis_client, "test:decorator_fail", timeout=10, blocking=False)
    async def decorated_function():
        return "should not execute"

    # Should raise RuntimeError
    with pytest.raises(RuntimeError, match="Failed to acquire lock"):
        await decorated_function()

    await lock.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_lock_decorator_releases_on_exception(redis_client):
    """Test with_lock decorator releases lock even on exception."""

    @with_lock(redis_client, "test:decorator_exception", timeout=10)
    async def decorated_function():
        raise ValueError("Test exception")

    # Should raise the exception
    with pytest.raises(ValueError, match="Test exception"):
        await decorated_function()

    # Lock should be released despite exception
    exists = await redis_client.exists("lock:test:decorator_exception")
    assert exists == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_with_lock_decorator_with_args_kwargs(redis_client):
    """Test with_lock decorator works with function args and kwargs."""

    @with_lock(redis_client, "test:decorator_args", timeout=10)
    async def decorated_function(a, b, c=None):
        return f"{a}-{b}-{c}"

    result = await decorated_function("foo", "bar", c="baz")

    assert result == "foo-bar-baz"

    # Lock should be released
    exists = await redis_client.exists("lock:test:decorator_args")
    assert exists == 0
