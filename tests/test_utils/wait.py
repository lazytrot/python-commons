"""
Condition-based waiting utilities for tests.

Eliminates race conditions by waiting for actual conditions instead of guessing timing.
Follows the condition-based-waiting skill pattern.
"""

import asyncio
from typing import Callable, Any, TypeVar

T = TypeVar("T")


async def wait_for_condition(
    condition: Callable[[], Any],
    description: str,
    timeout_ms: int = 5000,
    poll_interval_ms: int = 10,
) -> Any:
    """
    Wait for a condition to become truthy.

    Args:
        condition: Callable that returns truthy value when condition is met (can be async)
        description: Human-readable description for error messages
        timeout_ms: Maximum time to wait in milliseconds
        poll_interval_ms: How often to check condition in milliseconds

    Returns:
        The truthy value returned by condition

    Raises:
        TimeoutError: If condition not met within timeout

    Example:
        await wait_for_condition(
            lambda: len(messages) > 0,
            "messages to be received",
            timeout_ms=3000
        )
    """
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = timeout_ms / 1000
    poll_interval_seconds = poll_interval_ms / 1000

    while True:
        result = condition()
        # Handle both sync and async conditions
        if asyncio.iscoroutine(result):
            result = await result

        if result:
            return result

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"Timeout waiting for {description} after {timeout_ms}ms"
            )

        await asyncio.sleep(poll_interval_seconds)


async def wait_for_redis_key(
    redis_client,
    key: str,
    timeout_ms: int = 5000,
) -> bool:
    """
    Wait for a Redis key to exist.

    Args:
        redis_client: Redis client instance
        key: Key to wait for
        timeout_ms: Maximum time to wait in milliseconds

    Returns:
        True when key exists

    Raises:
        TimeoutError: If key doesn't exist within timeout
    """
    await wait_for_condition(
        lambda: asyncio.create_task(redis_client.exists(key)),
        f"Redis key '{key}' to exist",
        timeout_ms=timeout_ms,
    )
    return True


async def wait_for_redis_key_deleted(
    redis_client,
    key: str,
    timeout_ms: int = 5000,
) -> bool:
    """
    Wait for a Redis key to be deleted.

    Args:
        redis_client: Redis client instance
        key: Key to wait for deletion
        timeout_ms: Maximum time to wait in milliseconds

    Returns:
        True when key is deleted

    Raises:
        TimeoutError: If key still exists after timeout
    """

    async def check_deleted():
        exists = await redis_client.exists(key)
        return exists == 0

    await wait_for_condition(
        check_deleted,
        f"Redis key '{key}' to be deleted",
        timeout_ms=timeout_ms,
    )
    return True


async def wait_for_ttl_expiry(
    redis_client,
    key: str,
    timeout_ms: int = 5000,
) -> bool:
    """
    Wait for a Redis key's TTL to expire (key to be deleted).

    More efficient than sleep - checks every 10ms and stops immediately when expired.

    Args:
        redis_client: Redis client instance
        key: Key with TTL to wait for
        timeout_ms: Maximum time to wait in milliseconds

    Returns:
        True when key has expired

    Raises:
        TimeoutError: If key hasn't expired within timeout
    """
    return await wait_for_redis_key_deleted(redis_client, key, timeout_ms)


async def wait_for_lock_renewal(
    redis_client,
    lock_key: str,
    initial_ttl: int,
    timeout_ms: int = 5000,
) -> bool:
    """
    Wait for a distributed lock to be renewed (TTL refreshed).

    Args:
        redis_client: Redis client instance
        lock_key: Full lock key (including "lock:" prefix if applicable)
        initial_ttl: Initial TTL value before renewal
        timeout_ms: Maximum time to wait in milliseconds

    Returns:
        True when TTL has been refreshed

    Raises:
        TimeoutError: If lock not renewed within timeout
    """

    async def check_renewed():
        current_ttl = await redis_client.ttl(lock_key)
        # TTL was refreshed if it's greater than initial (accounting for time passed)
        return current_ttl > initial_ttl - 1

    await wait_for_condition(
        check_renewed,
        f"lock '{lock_key}' to be renewed",
        timeout_ms=timeout_ms,
    )
    return True
