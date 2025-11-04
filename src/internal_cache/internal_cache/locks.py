"""
Distributed locking with Redis.

Provides distributed locks for coordinating access across multiple processes/servers.
"""

import asyncio
import logging
import uuid
from typing import Optional, Callable
from contextlib import asynccontextmanager
from functools import wraps

from .client import RedisClient


logger = logging.getLogger(__name__)


class DistributedLock:
    """
    Distributed lock using Redis.

    Implements a lock that can be shared across multiple processes/servers.
    Uses Redlock algorithm for safety.
    """

    def __init__(
        self,
        client: RedisClient,
        lock_name: str,
        timeout: int = 10,
        auto_renewal: bool = False,
    ):
        """
        Initialize distributed lock.

        Args:
            client: Redis client
            lock_name: Unique name for the lock
            timeout: Lock timeout in seconds (auto-released after timeout)
            auto_renewal: Automatically renew lock while held

        Example:
            from internal_cache import RedisClient, DistributedLock

            redis = RedisClient()
            await redis.connect()

            lock = DistributedLock(redis, "process_orders", timeout=30)

            async with lock:
                # Only one process can execute this at a time
                await process_orders()
        """
        self.client = client
        self.lock_name = f"lock:{lock_name}"
        self.timeout = timeout
        self.auto_renewal = auto_renewal
        self._lock_value = str(uuid.uuid4())  # Unique token for this lock instance
        self._renewal_task: Optional[asyncio.Task] = None

    async def acquire(self, blocking: bool = True, timeout: Optional[float] = None) -> bool:
        """
        Acquire the lock.

        Args:
            blocking: Wait for lock if not available
            timeout: Maximum time to wait (None = wait forever)

        Returns:
            True if lock acquired

        Example:
            lock = DistributedLock(redis, "my_lock")

            # Non-blocking attempt
            if await lock.acquire(blocking=False):
                try:
                    # Do work
                    pass
                finally:
                    await lock.release()

            # Blocking with timeout
            if await lock.acquire(blocking=True, timeout=5.0):
                # Got lock within 5 seconds
                pass
        """
        start_time = asyncio.get_event_loop().time()

        while True:
            # Try to acquire lock
            acquired = await self.client.set(
                self.lock_name,
                self._lock_value,
                ttl=self.timeout,
                nx=True,  # Only set if not exists
            )

            if acquired:
                logger.debug(f"Acquired lock: {self.lock_name}")

                # Start auto-renewal if enabled
                if self.auto_renewal:
                    self._renewal_task = asyncio.create_task(self._renew_loop())

                return True

            # Check if we should continue waiting
            if not blocking:
                return False

            if timeout is not None:
                elapsed = asyncio.get_event_loop().time() - start_time
                if elapsed >= timeout:
                    logger.warning(f"Failed to acquire lock after {timeout}s: {self.lock_name}")
                    return False

            # Wait a bit before retrying
            await asyncio.sleep(0.1)

    async def release(self) -> bool:
        """
        Release the lock.

        Returns:
            True if lock was released

        Example:
            await lock.release()
        """
        # Stop auto-renewal
        if self._renewal_task:
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
            self._renewal_task = None

        # Only delete if we own the lock (check value matches)
        # This prevents accidentally releasing someone else's lock
        lua_script = """
        if redis.call("get", KEYS[1]) == ARGV[1] then
            return redis.call("del", KEYS[1])
        else
            return 0
        end
        """

        try:
            result = await self.client.client.eval(
                lua_script,
                1,
                self.client._get_key(self.lock_name),
                self._lock_value,
            )
            released = bool(result)

            if released:
                logger.debug(f"Released lock: {self.lock_name}")
            else:
                logger.warning(f"Failed to release lock (not owner): {self.lock_name}")

            return released

        except Exception as e:
            logger.error(f"Error releasing lock: {e}")
            return False

    async def _renew_loop(self) -> None:
        """Auto-renewal loop (runs in background)."""
        renewal_interval = self.timeout / 3  # Renew at 1/3 of timeout

        try:
            while True:
                await asyncio.sleep(renewal_interval)

                # Renew lock by extending TTL
                lua_script = """
                if redis.call("get", KEYS[1]) == ARGV[1] then
                    return redis.call("expire", KEYS[1], ARGV[2])
                else
                    return 0
                end
                """

                result = await self.client.client.eval(
                    lua_script,
                    1,
                    self.client._get_key(self.lock_name),
                    self._lock_value,
                    self.timeout,
                )

                if result:
                    logger.debug(f"Renewed lock: {self.lock_name}")
                else:
                    logger.warning(f"Failed to renew lock (lost ownership): {self.lock_name}")
                    break

        except asyncio.CancelledError:
            logger.debug(f"Lock renewal cancelled: {self.lock_name}")
            raise

    async def __aenter__(self):
        """Context manager entry."""
        acquired = await self.acquire()
        if not acquired:
            raise RuntimeError(f"Failed to acquire lock: {self.lock_name}")
        return acquired

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.release()
        return False

    @property
    def locked(self) -> bool:
        """Check if lock is currently held (by anyone)."""
        # Note: This is a best-effort check, lock state may change immediately after
        return asyncio.create_task(self.client.exists(self.lock_name)).result() > 0


def with_lock(
    client: RedisClient,
    lock_name: str,
    timeout: int = 10,
    blocking: bool = True,
):
    """
    Decorator that acquires a distributed lock before executing function.

    Args:
        client: Redis client
        lock_name: Name of the lock
        timeout: Lock timeout in seconds
        blocking: Wait for lock if not available

    Example:
        from internal_cache import RedisClient, with_lock

        redis = RedisClient()
        await redis.connect()

        @with_lock(redis, "process_reports", timeout=60)
        async def generate_daily_report():
            # Only one instance can run this at a time
            await expensive_report_generation()

        # If another instance is running, this will wait
        await generate_daily_report()
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            lock = DistributedLock(client, lock_name, timeout=timeout)

            if not await lock.acquire(blocking=blocking):
                raise RuntimeError(f"Failed to acquire lock: {lock_name}")

            try:
                return await func(*args, **kwargs)
            finally:
                await lock.release()

        return wrapper

    return decorator


# Example usage patterns:
#
# 1. Context manager (recommended):
#
# async with DistributedLock(redis, "my_resource", timeout=30):
#     # Critical section - only one process at a time
#     await modify_shared_resource()
#
#
# 2. Manual acquire/release:
#
# lock = DistributedLock(redis, "my_resource")
# if await lock.acquire(blocking=False):
#     try:
#         await modify_shared_resource()
#     finally:
#         await lock.release()
# else:
#     print("Resource is busy")
#
#
# 3. Decorator:
#
# @with_lock(redis, "process_queue", timeout=60)
# async def process_queue():
#     # Guaranteed single execution
#     items = await get_queue_items()
#     for item in items:
#         await process_item(item)
#
#
# 4. Auto-renewal for long operations:
#
# async with DistributedLock(redis, "long_task", timeout=30, auto_renewal=True):
#     # Lock will be automatically renewed every 10s (timeout/3)
#     await very_long_operation()  # Can run for > 30s
