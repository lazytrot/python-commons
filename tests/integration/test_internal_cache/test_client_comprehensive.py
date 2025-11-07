"""
Comprehensive integration tests for Redis client to achieve 100% coverage.

Tests all uncovered lines with real Redis testcontainers.
Uses shared session-scoped Redis container from root conftest.py for speed.
"""

import pytest

# Note: redis_client and redis_config fixtures are provided by tests/conftest.py with session-scoped Redis container



@pytest.mark.integration
@pytest.mark.asyncio
async def test_client_connect_already_connected(redis_client):
    """Test that connect() is idempotent when already connected."""
    # Client is already connected from fixture
    first_client = redis_client._client

    # Call connect again
    await redis_client.connect()

    # Should be the same client instance
    assert redis_client._client is first_client



@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_with_default(redis_client):
    """Test get with default value when key doesn't exist."""
    value = await redis_client.get("nonexistent:key", default="default_value")

    assert value == "default_value"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_with_json_deserialization(redis_client):
    """Test get deserializes JSON automatically."""
    await redis_client.set("test:json", {"key": "value"})

    value = await redis_client.get("test:json")

    assert isinstance(value, dict)
    assert value["key"] == "value"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_with_non_json_value(redis_client):
    """Test get returns raw value when JSON deserialization fails."""
    # Set a raw string value using the underlying client
    await redis_client.client.set(
        redis_client._get_key("test:raw"),
        "plain_string_not_json"
    )

    value = await redis_client.get("test:raw")

    assert value == "plain_string_not_json"



@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_with_nx_flag(redis_client):
    """Test set with nx flag (only set if not exists)."""
    # First set should succeed
    result1 = await redis_client.set("test:nx", "value1", nx=True)
    assert result1 is True

    # Second set should fail (key exists)
    result2 = await redis_client.set("test:nx", "value2", nx=True)
    assert result2 is False

    # Value should still be "value1"
    value = await redis_client.get("test:nx")
    assert value == "value1"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_with_xx_flag(redis_client):
    """Test set with xx flag (only set if exists)."""
    # First set should fail (key doesn't exist)
    result1 = await redis_client.set("test:xx", "value1", xx=True)
    assert result1 is False

    # Create the key
    await redis_client.set("test:xx", "initial")

    # Second set should succeed (key exists)
    result2 = await redis_client.set("test:xx", "value2", xx=True)
    assert result2 is True

    # Value should be "value2"
    value = await redis_client.get("test:xx")
    assert value == "value2"





@pytest.mark.integration
@pytest.mark.asyncio
async def test_expire_success(redis_client):
    """Test expire sets TTL successfully."""
    await redis_client.set("test:expire", "value")

    result = await redis_client.expire("test:expire", 10)

    assert result is True

    # Verify TTL is set
    ttl = await redis_client.ttl("test:expire")
    assert ttl > 0





@pytest.mark.integration
@pytest.mark.asyncio
async def test_decrement_success(redis_client):
    """Test decrement decrements value successfully."""
    await redis_client.set("test:decr", "10")

    result = await redis_client.decrement("test:decr")

    assert result == 9



@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_keys_with_pattern(redis_client):
    """Test scan_keys finds matching keys."""
    # Create multiple keys
    await redis_client.set("user:1", "data1")
    await redis_client.set("user:2", "data2")
    await redis_client.set("product:1", "data3")

    # Scan for user keys
    keys = await redis_client.scan_keys("user:*")

    assert len(keys) == 2
    assert "user:1" in keys
    assert "user:2" in keys


@pytest.mark.integration
@pytest.mark.asyncio
async def test_scan_keys_with_count(redis_client):
    """Test scan_keys with custom count parameter."""
    # Create many keys
    for i in range(20):
        await redis_client.set(f"item:{i}", f"value{i}")

    # Scan with small count
    keys = await redis_client.scan_keys("item:*", count=5)

    assert len(keys) == 20



@pytest.mark.integration
@pytest.mark.asyncio
async def test_flush_pattern_with_matching_keys(redis_client):
    """Test flush_pattern deletes matching keys."""
    await redis_client.set("session:1", "data1")
    await redis_client.set("session:2", "data2")
    await redis_client.set("user:1", "data3")

    count = await redis_client.flush_pattern("session:*")

    assert count == 2

    # Verify session keys are deleted
    exists1 = await redis_client.exists("session:1")
    exists2 = await redis_client.exists("session:2")
    assert exists1 == 0
    assert exists2 == 0

    # Verify user key still exists
    exists3 = await redis_client.exists("user:1")
    assert exists3 > 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_flush_pattern_with_no_matches(redis_client):
    """Test flush_pattern returns 0 when no keys match."""
    count = await redis_client.flush_pattern("nonexistent:*")

    assert count == 0





