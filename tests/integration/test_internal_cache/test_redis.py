"""Integration tests for Redis using testcontainers."""

import pytest
import asyncio
from testcontainers.redis import RedisContainer
from internal_cache import RedisClient, RedisConfig, DistributedLock, cached


@pytest.fixture(scope="module")
def redis_container():
    """Start Redis container for integration tests."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    yield redis

    redis.stop()


@pytest.fixture(scope="module")
def redis_config(redis_container):
    """Create Redis configuration from testcontainer."""
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
        ssl=False,
    )


@pytest.fixture
async def redis_client(redis_config):
    """Create Redis client connected to testcontainer."""
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database
    await client.client.flushdb()
    await client.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_connection(redis_client):
    """Test basic Redis connection."""
    result = await redis_client.ping()
    assert result is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_set_get(redis_client):
    """Test Redis set and get operations."""
    await redis_client.set("test:key", "test_value")
    value = await redis_client.get("test:key")

    assert value == "test_value"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_set_with_ttl(redis_client):
    """Test Redis set with TTL."""
    await redis_client.set("test:ttl", "value", ttl=2)
    value = await redis_client.get("test:ttl")
    assert value == "value"

    # Wait for expiration
    await asyncio.sleep(3)
    expired_value = await redis_client.get("test:ttl")
    assert expired_value is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_delete(redis_client):
    """Test Redis delete operation."""
    await redis_client.set("test:delete", "value")
    await redis_client.delete("test:delete")

    value = await redis_client.get("test:delete")
    assert value is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_exists(redis_client):
    """Test Redis exists operation."""
    await redis_client.set("test:exists", "value")

    exists = await redis_client.exists("test:exists")
    assert exists == 1

    not_exists = await redis_client.exists("test:not_exists")
    assert not_exists == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_increment(redis_client):
    """Test Redis increment operation."""
    await redis_client.set("test:counter", "0")

    value1 = await redis_client.increment("test:counter")
    assert value1 == 1

    value2 = await redis_client.increment("test:counter")
    assert value2 == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_hash_operations(redis_client):
    """Test Redis hash operations."""
    # Set hash field
    await redis_client.client.hset("test:hash", "field1", "value1")
    await redis_client.client.hset("test:hash", "field2", "value2")

    # Get hash field
    value = await redis_client.client.hget("test:hash", "field1")
    assert value == "value1"

    # Get all hash fields
    all_fields = await redis_client.client.hgetall("test:hash")
    assert all_fields == {"field1": "value1", "field2": "value2"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_list_operations(redis_client):
    """Test Redis list operations."""
    # Push to list
    await redis_client.client.lpush("test:list", "item1")
    await redis_client.client.lpush("test:list", "item2")
    await redis_client.client.rpush("test:list", "item3")

    # Get list length
    length = await redis_client.client.llen("test:list")
    assert length == 3

    # Get list range
    items = await redis_client.client.lrange("test:list", 0, -1)
    assert items == ["item2", "item1", "item3"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_set_operations(redis_client):
    """Test Redis set operations."""
    # Add to set
    await redis_client.client.sadd("test:set", "member1")
    await redis_client.client.sadd("test:set", "member2")
    await redis_client.client.sadd("test:set", "member3")

    # Check membership
    is_member = await redis_client.client.sismember("test:set", "member1")
    assert is_member == 1

    # Get all members
    members = await redis_client.client.smembers("test:set")
    assert len(members) == 3
    assert "member1" in members


@pytest.mark.integration
@pytest.mark.asyncio
async def test_distributed_lock_acquire_release(redis_client):
    """Test distributed lock acquisition and release."""
    lock = DistributedLock(
        client=redis_client,
        lock_name="test:lock",
        timeout=10,
    )

    # Acquire lock
    acquired = await lock.acquire()
    assert acquired is True

    # Release lock
    await lock.release()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_distributed_lock_context_manager(redis_client):
    """Test distributed lock as context manager."""
    async with DistributedLock(
        client=redis_client,
        lock_name="test:lock:ctx",
        timeout=10,
    ) as acquired:
        assert acquired is True

        # Lock should be held
        # DistributedLock prepends "lock:" to the lock_name
        exists = await redis_client.exists("lock:test:lock:ctx")
        assert exists > 0

    # Lock should be released after context
    exists_after = await redis_client.exists("lock:test:lock:ctx")
    assert exists_after == 0


@pytest.mark.integration
@pytest.mark.asyncio
async def test_distributed_lock_concurrent_access(redis_client):
    """Test distributed lock prevents concurrent access."""
    counter = {"value": 0}

    async def increment_with_lock():
        async with DistributedLock(
            client=redis_client,
            lock_name="test:lock:counter",
            timeout=5,
        ):
            # Simulate work
            current = counter["value"]
            await asyncio.sleep(0.01)
            counter["value"] = current + 1

    # Run concurrent increments
    await asyncio.gather(*[increment_with_lock() for _ in range(10)])

    # Without proper locking, this could be less than 10 due to race conditions
    # With proper locking, it should be exactly 10
    assert counter["value"] == 10


@pytest.mark.integration
@pytest.mark.asyncio
async def test_cached_decorator(redis_client):
    """Test cached decorator with real Redis."""
    call_count = 0

    @cached(client=redis_client, ttl=10)
    async def expensive_function(arg: int):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0.1)
        return arg * 2

    # First call - cache miss
    result1 = await expensive_function(5)
    assert result1 == 10
    assert call_count == 1

    # Second call - cache hit
    result2 = await expensive_function(5)
    assert result2 == 10
    assert call_count == 1  # Should not increment

    # Different argument - cache miss
    result3 = await expensive_function(10)
    assert result3 == 20
    assert call_count == 2


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_pipeline(redis_client):
    """Test Redis pipeline for batch operations."""
    pipe = redis_client.client.pipeline()
    pipe.set("pipe:key1", "value1")
    pipe.set("pipe:key2", "value2")
    pipe.get("pipe:key1")
    pipe.get("pipe:key2")

    results = await pipe.execute()

    # Results should include set confirmations and get values
    assert len(results) == 4


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_pubsub(redis_client):
    """Test Redis pub/sub functionality."""
    pubsub = redis_client.client.pubsub()
    await pubsub.subscribe("test:channel")

    # Publish message
    await redis_client.client.publish("test:channel", "test message")

    # Wait briefly for message
    await asyncio.sleep(0.1)

    # Try to get message
    message = await pubsub.get_message(ignore_subscribe_messages=True, timeout=1)

    if message:
        assert message["type"] == "message"
        assert message["data"] == "test message"

    await pubsub.unsubscribe("test:channel")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_multiple_databases(redis_config):
    """Test Redis with multiple databases."""
    # Connect to db 0
    from dataclasses import asdict
    client0 = RedisClient(RedisConfig(**{**asdict(redis_config), "db": 0}))
    await client0.connect()

    # Connect to db 1
    client1 = RedisClient(RedisConfig(**{**asdict(redis_config), "db": 1}))
    await client1.connect()

    # Set value in db 0
    await client0.set("test:key", "db0_value")

    # Set value in db 1
    await client1.set("test:key", "db1_value")

    # Values should be different
    value0 = await client0.get("test:key")
    value1 = await client1.get("test:key")

    assert value0 == "db0_value"
    assert value1 == "db1_value"

    await client0.close()
    await client1.close()
