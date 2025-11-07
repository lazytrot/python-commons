"""
Comprehensive integration tests for cache decorators to achieve 100% coverage.

Tests all uncovered lines with real Redis testcontainers.
Uses shared session-scoped Redis container from root conftest.py for speed.
"""

import pytest
import asyncio
from internal_cache import cached, cache_aside
from internal_cache.decorators import _generate_cache_key, _invalidate_cache

# Note: redis_client fixture is provided by tests/conftest.py with session-scoped Redis container


class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_generate_cache_key_with_json_serializable_args(self):
        """Test key generation with JSON-serializable arguments."""

        def test_func(a, b):
            pass

        key = _generate_cache_key(test_func, (1, 2), {})

        assert "test_func" in key
        assert "cache:" in key

    def test_generate_cache_key_with_non_json_args(self):
        """Test key generation with non-JSON-serializable arguments."""

        def test_func(obj):
            pass

        class CustomClass:
            def __str__(self):
                return "custom_object"

        obj = CustomClass()
        key = _generate_cache_key(test_func, (obj,), {})

        assert "test_func" in key
        assert "cache:" in key

    def test_generate_cache_key_with_json_kwargs(self):
        """Test key generation with JSON-serializable kwargs."""

        def test_func(a, b=None):
            pass

        key = _generate_cache_key(test_func, (1,), {"b": 2})

        assert "test_func" in key
        assert "b=" in key

    def test_generate_cache_key_with_non_json_kwargs(self):
        """Test key generation with non-JSON-serializable kwargs."""

        def test_func(obj=None):
            pass

        class CustomClass:
            def __str__(self):
                return "custom_object"

        obj = CustomClass()
        key = _generate_cache_key(test_func, (), {"obj": obj})

        assert "test_func" in key

    def test_generate_cache_key_long_key_hashing(self):
        """Test that long keys are hashed."""

        def test_func_with_very_long_name_that_should_trigger_hashing():
            pass

        # Create very long arguments to trigger hashing
        long_args = tuple([f"arg_{i}" * 10 for i in range(20)])
        key = _generate_cache_key(
            test_func_with_very_long_name_that_should_trigger_hashing,
            long_args,
            {}
        )

        # Should be hashed and shorter
        assert len(key) < 300
        assert ":" in key


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_with_key_prefix(redis_client):
    """Test cached decorator with key prefix."""
    call_count = 0

    @cached(redis_client, ttl=10, key_prefix="myapp")
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Cache hit
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_with_custom_key_builder(redis_client):
    """Test cached decorator with custom key builder."""
    call_count = 0

    def custom_key_builder(func, args, kwargs):
        return f"custom:{args[0]}"

    @cached(redis_client, ttl=10, key_builder=custom_key_builder)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Verify custom key was used
    exists = await redis_client.exists("custom:5")
    assert exists > 0

    # Cache hit
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_cache_get_exception(redis_client):
    """Test cached decorator handles cache get exceptions gracefully."""
    call_count = 0

    @cached(redis_client, ttl=10)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    # Close connection to simulate error
    await redis_client.close()

    # Should still execute function despite cache error
    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Reconnect for cleanup
    await redis_client.connect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_cache_set_exception(redis_client):
    """Test cached decorator handles cache set exceptions gracefully."""
    call_count = 0

    @cached(redis_client, ttl=10)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        # Close connection during function execution to cause set error
        if call_count == 1:
            await redis_client.close()
        return value * 2

    # Should execute function and handle cache set error
    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Reconnect for cleanup
    await redis_client.connect()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_invalidate_with_default_key(redis_client):
    """Test cache invalidation with default key generation."""
    call_count = 0

    @cached(redis_client, ttl=10)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    # First call
    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Invalidate cache
    invalidated = await get_data.cache_invalidate(5)
    assert invalidated is True

    # Should call function again
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_invalidate_with_custom_key_builder(redis_client):
    """Test cache invalidation with custom key builder."""
    call_count = 0

    def custom_key_builder(func, args, kwargs):
        return f"custom:{args[0]}"

    @cached(redis_client, ttl=10, key_builder=custom_key_builder)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    # First call
    result = await get_data(5)
    assert result == 10

    # Invalidate cache
    invalidated = await get_data.cache_invalidate(5)
    assert invalidated is True

    # Should call function again
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_invalidate_with_key_prefix(redis_client):
    """Test cache invalidation with key prefix."""
    call_count = 0

    @cached(redis_client, ttl=10, key_prefix="app")
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    # First call
    result = await get_data(5)
    assert result == 10

    # Invalidate cache
    invalidated = await get_data.cache_invalidate(5)
    assert invalidated is True

    # Should call function again
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_invalidate_cache_returns_false_when_not_exists(redis_client):
    """Test _invalidate_cache returns False when key doesn't exist."""

    def test_func(value):
        pass

    result = await _invalidate_cache(
        redis_client,
        test_func,
        None,
        None,
        (5,),
        {}
    )

    assert result is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_aside_with_default_key(redis_client):
    """Test cache_aside decorator with default key generation."""
    call_count = 0

    @cache_aside(redis_client, ttl=10)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    result = await get_data(5)
    assert result == 10
    assert call_count == 1

    # Cache hit
    result2 = await get_data(5)
    assert result2 == 10
    assert call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_aside_with_custom_key_func(redis_client):
    """Test cache_aside decorator with custom key function."""
    call_count = 0

    @cache_aside(redis_client, ttl=10, key_func=lambda user_id: f"user:{user_id}")
    async def get_user_data(user_id):
        nonlocal call_count
        call_count += 1
        return {"id": user_id, "name": f"User{user_id}"}

    result = await get_user_data(123)
    assert result["id"] == 123
    assert call_count == 1

    # Verify custom key was used
    exists = await redis_client.exists("user:123")
    assert exists > 0

    # Cache hit
    result2 = await get_user_data(123)
    assert result2["id"] == 123
    assert call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cache_aside_without_key_func(redis_client):
    """Test cache_aside decorator without key_func uses default."""
    call_count = 0

    @cache_aside(redis_client, ttl=10)
    async def get_data(value):
        nonlocal call_count
        call_count += 1
        return value * 2

    result = await get_data(7)
    assert result == 14
    assert call_count == 1

    # Cache hit
    result2 = await get_data(7)
    assert result2 == 14
    assert call_count == 1


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_with_complex_types(redis_client):
    """Test cached decorator with complex data types."""
    call_count = 0

    @cached(redis_client, ttl=10)
    async def get_complex_data(key):
        nonlocal call_count
        call_count += 1
        return {
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
            "number": 42
        }

    result = await get_complex_data("test")
    assert result["list"] == [1, 2, 3]
    assert call_count == 1

    # Cache hit
    result2 = await get_complex_data("test")
    assert result2["dict"]["nested"] == "value"
    assert call_count == 1
