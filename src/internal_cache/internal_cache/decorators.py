"""
Caching decorators for function memoization.

Provides decorators for automatic caching with Redis.
"""

import hashlib
import json
import logging
from typing import Callable, Optional, Any
from functools import wraps

from .client import RedisClient


logger = logging.getLogger(__name__)


def _generate_cache_key(func: Callable, args: tuple, kwargs: dict) -> str:
    """
    Generate cache key from function name and arguments.

    Args:
        func: Function being cached
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Cache key string
    """
    # Create a deterministic representation of arguments
    key_parts = [func.__module__, func.__name__]

    # Add args
    for arg in args:
        try:
            key_parts.append(json.dumps(arg, sort_keys=True))
        except (TypeError, ValueError):
            key_parts.append(str(arg))

    # Add kwargs
    for k in sorted(kwargs.keys()):
        try:
            key_parts.append(f"{k}={json.dumps(kwargs[k], sort_keys=True)}")
        except (TypeError, ValueError):
            key_parts.append(f"{k}={kwargs[k]}")

    # Hash the key if it's too long
    key_string = ":".join(key_parts)
    if len(key_string) > 200:
        key_hash = hashlib.md5(key_string.encode()).hexdigest()
        return f"cache:{func.__name__}:{key_hash}"

    return f"cache:{key_string}"


def cached(
    client: RedisClient,
    ttl: int = 3600,
    key_prefix: Optional[str] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results in Redis.

    Args:
        client: Redis client instance
        ttl: Time-to-live in seconds (default: 1 hour)
        key_prefix: Optional key prefix
        key_builder: Optional custom key builder function

    Example:
        from internal_cache import RedisClient, cached

        redis = RedisClient()
        await redis.connect()

        @cached(redis, ttl=300)
        async def get_user(user_id: int):
            # This will be cached for 5 minutes
            return await db.fetch_user(user_id)

        # First call hits database
        user = await get_user(123)

        # Second call returns cached result
        user = await get_user(123)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_builder:
                cache_key = key_builder(func, args, kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            if key_prefix:
                cache_key = f"{key_prefix}:{cache_key}"

            # Try to get from cache
            try:
                cached_value = await client.get(cache_key)
                if cached_value is not None:
                    logger.debug(f"Cache hit: {cache_key}")
                    return cached_value
            except Exception as e:
                logger.warning(f"Cache get failed: {e}")

            # Cache miss - execute function
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            # Store in cache
            try:
                await client.set(cache_key, result, ttl=ttl)
                logger.debug(f"Cached result: {cache_key} (ttl={ttl}s)")
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

            return result

        # Add cache control methods
        wrapper.cache_invalidate = lambda *args, **kwargs: _invalidate_cache(
            client, func, key_prefix, key_builder, args, kwargs
        )

        return wrapper

    return decorator


async def _invalidate_cache(
    client: RedisClient,
    func: Callable,
    key_prefix: Optional[str],
    key_builder: Optional[Callable],
    args: tuple,
    kwargs: dict,
) -> bool:
    """
    Invalidate cache for specific function call.

    Args:
        client: Redis client
        func: Function
        key_prefix: Key prefix
        key_builder: Key builder function
        args: Function args
        kwargs: Function kwargs

    Returns:
        True if cache was invalidated
    """
    if key_builder:
        cache_key = key_builder(func, args, kwargs)
    else:
        cache_key = _generate_cache_key(func, args, kwargs)

    if key_prefix:
        cache_key = f"{key_prefix}:{cache_key}"

    deleted = await client.delete(cache_key)
    return deleted > 0


def cache_aside(
    client: RedisClient,
    ttl: int = 3600,
    key_func: Optional[Callable] = None,
):
    """
    Cache-aside pattern decorator.

    Similar to @cached but with explicit control over cache key.

    Args:
        client: Redis client instance
        ttl: Time-to-live in seconds
        key_func: Function to generate cache key from args/kwargs

    Example:
        @cache_aside(redis, ttl=600, key_func=lambda user_id: f"user:{user_id}")
        async def get_user_data(user_id: int):
            return await fetch_from_db(user_id)

        # Cache key will be "user:123"
        data = await get_user_data(123)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Generate cache key
            if key_func:
                cache_key = key_func(*args, **kwargs)
            else:
                cache_key = _generate_cache_key(func, args, kwargs)

            # Check cache
            cached_value = await client.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit: {cache_key}")
                return cached_value

            # Execute and cache
            logger.debug(f"Cache miss: {cache_key}")
            result = await func(*args, **kwargs)

            await client.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


# Example usage with manual cache control:
#
# from internal_cache import RedisClient, cached
#
# redis = RedisClient()
# await redis.connect()
#
# @cached(redis, ttl=300)
# async def get_product(product_id: int):
#     return await db.fetch_product(product_id)
#
# # Get from cache or DB
# product = await get_product(123)
#
# # Update product in DB
# await db.update_product(123, {"price": 99.99})
#
# # Invalidate cache
# await get_product.cache_invalidate(123)
#
# # Next call will fetch fresh data
# product = await get_product(123)
