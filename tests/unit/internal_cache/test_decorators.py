"""
Unit tests for caching decorators.

Tests cached and cache_aside decorators.
"""

import pytest
import json
from internal_cache.decorators import _generate_cache_key, cached, cache_aside, _invalidate_cache
from internal_cache import RedisClient, RedisConfig


class TestGenerateCacheKey:
    """Test cache key generation."""

    def test_simple_function(self):
        """Test key generation for simple function."""
        def my_func(a, b):
            return a + b

        key = _generate_cache_key(my_func, (1, 2), {})
        assert "my_func" in key
        assert "cache:" in key

    def test_with_kwargs(self):
        """Test key generation with kwargs."""
        def my_func(a, b=10):
            return a + b

        key = _generate_cache_key(my_func, (1,), {"b": 20})
        assert "my_func" in key
        assert "b=" in key

    def test_long_key_hashing(self):
        """Test that long keys are hashed."""
        def my_func_with_very_long_name_that_exceeds_limit(*args):
            pass

        # Create args that will make key > 200 chars
        long_args = tuple(["x" * 50 for _ in range(10)])
        key = _generate_cache_key(my_func_with_very_long_name_that_exceeds_limit, long_args, {})

        # Should be hashed
        assert len(key) < 200
        assert "cache:my_func_with_very_long_name_that_exceeds_limit:" in key

    def test_json_serializable_args(self):
        """Test with JSON serializable arguments."""
        def my_func(data):
            return data

        key = _generate_cache_key(my_func, ({"key": "value"},), {})
        assert "my_func" in key

    def test_non_json_serializable_args(self):
        """Test with non-JSON serializable arguments."""
        class CustomClass:
            def __str__(self):
                return "custom"

        def my_func(obj):
            return obj

        obj = CustomClass()
        key = _generate_cache_key(my_func, (obj,), {})
        assert "my_func" in key
        assert "custom" in key
