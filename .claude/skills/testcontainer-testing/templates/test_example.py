"""Example test file structure for testcontainer-based tests."""

import pytest


# PostgreSQL Example Tests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_postgres_example(db_session):
    """Example PostgreSQL test.

    Uses db_session fixture which provides:
    - Clean database with tables created
    - Automatic cleanup after test
    """
    from sqlalchemy import select
    from conftest import YourModel  # Import your model

    # Create
    item = YourModel(name="test")
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    # Read
    stmt = select(YourModel).where(YourModel.name == "test")
    result = await db_session.execute(stmt)
    found = result.scalar_one()

    assert found.name == "test"
    assert found.id is not None


# Redis Example Tests


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_example(redis_client):
    """Example Redis test.

    Uses redis_client fixture which provides:
    - Connected Redis client
    - Automatic cleanup (flushdb) after test
    """
    # Set value
    await redis_client.set("test:key", "test_value")

    # Get value
    value = await redis_client.get("test:key")

    assert value == "test_value"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_redis_lock_example(redis_client):
    """Example distributed lock test."""
    from internal_cache import DistributedLock

    async with DistributedLock(
        client=redis_client,
        lock_name="test:lock",
        timeout=5,
    ) as acquired:
        assert acquired is True
        # Do work under lock


# S3 Example Tests


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
async def test_s3_example(s3_client):
    """Example S3 test.

    Uses s3_client fixture which provides:
    - S3 client connected to LocalStack
    - Bucket already created
    """
    # Upload
    await s3_client.put_object("test.txt", b"Hello, World!")

    # Download
    content = await s3_client.get_object_as_bytes("test.txt")

    assert content == b"Hello, World!"


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
async def test_s3_json_example(s3_client):
    """Example S3 JSON operations."""
    import json

    data = {"key": "value", "number": 42}

    # Upload JSON
    await s3_client.put_object(
        "data.json", json.dumps(data), content_type="application/json"
    )

    # Download and parse JSON
    retrieved = await s3_client.get_object_as_json("data.json")

    assert retrieved == data


# DynamoDB Example Tests


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
async def test_dynamodb_example(dynamodb_table):
    """Example DynamoDB test.

    Uses dynamodb_table fixture which provides:
    - DynamoDB table connected to LocalStack
    - Table already created with schema
    """
    from conftest import YourItem  # Import your item model

    # Put item
    item = YourItem(id="123", name="test")
    await dynamodb_table.put_item(item)

    # Get item
    retrieved = await dynamodb_table.get_item({"id": "123"})

    assert retrieved.id == "123"
    assert retrieved.name == "test"


# Best Practices Demonstrated


@pytest.mark.integration
@pytest.mark.asyncio
async def test_transaction_rollback(db_session):
    """Example showing transaction rollback."""
    from conftest import YourModel

    # Create item
    item = YourModel(name="original")
    db_session.add(item)
    await db_session.commit()
    await db_session.refresh(item)

    # Modify but rollback
    item.name = "modified"

    # Rollback instead of commit
    await db_session.rollback()

    # Refresh to get database state
    await db_session.refresh(item)

    # Name should still be original
    assert item.name == "original"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_operations(redis_client):
    """Example showing concurrent operations with locks."""
    import asyncio
    from internal_cache import DistributedLock

    counter = {"value": 0}

    async def increment_with_lock():
        async with DistributedLock(
            client=redis_client,
            lock_name="test:counter",
            timeout=5,
        ):
            # Simulate work
            current = counter["value"]
            await asyncio.sleep(0.01)
            counter["value"] = current + 1

    # Run 10 concurrent increments
    await asyncio.gather(*[increment_with_lock() for _ in range(10)])

    # With proper locking, should be exactly 10
    assert counter["value"] == 10
