# Service-Specific Testcontainer Examples

This document provides complete, copy-paste examples for common services.

## PostgreSQL

### Complete Setup

```python
# tests/integration/test_postgres/conftest.py

import pytest
import pytest_asyncio
from testcontainers.postgres import PostgresContainer
from sqlalchemy import Column, Integer, String
from internal_rdbms import (
    Base,
    DatabaseConfig,
    DatabaseDriver,
    DatabaseSessionManager,
    TimestampMixin,
)


# Example model for testing
class User(Base, TimestampMixin):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False, unique=True)
    email = Column(String(100), nullable=False)


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for test session."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres


@pytest.fixture
def postgres_config(postgres_container):
    """Create database configuration from container."""
    return DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
        pool_size=5,
        max_overflow=10,
    )


@pytest_asyncio.fixture
async def db_session(postgres_config):
    """Create database session with automatic table setup/cleanup."""
    manager = DatabaseSessionManager(postgres_config)

    # Create tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager() as session:
        yield session

    # Cleanup
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await manager.close()
```

### Example Tests

```python
# tests/integration/test_postgres/test_database.py

import pytest
from sqlalchemy import select


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user(db_session):
    """Test creating a user."""
    user = User(username="testuser", email="test@example.com")
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    assert user.id is not None
    assert user.created_at is not None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_query_users(db_session):
    """Test querying users."""
    # Create users
    users = [
        User(username="alice", email="alice@example.com"),
        User(username="bob", email="bob@example.com"),
    ]
    db_session.add_all(users)
    await db_session.commit()

    # Query
    stmt = select(User).where(User.username == "alice")
    result = await db_session.execute(stmt)
    alice = result.scalar_one()

    assert alice.username == "alice"
```

## Redis

### Complete Setup

```python
# tests/integration/test_redis/conftest.py

import pytest
import pytest_asyncio
from testcontainers.redis import RedisContainer
from internal_cache import RedisClient, RedisConfig


@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container for test session."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    yield redis

    redis.stop()


@pytest.fixture
def redis_config(redis_container):
    """Create Redis configuration from container."""
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
        ssl=False,
    )


@pytest_asyncio.fixture
async def redis_client(redis_config):
    """Create Redis client with automatic cleanup."""
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database
    await client.client.flushdb()
    await client.close()
```

### Example Tests

```python
# tests/integration/test_redis/test_cache.py

import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_set_get(redis_client):
    """Test basic Redis operations."""
    await redis_client.set("key", "value")
    result = await redis_client.get("key")
    assert result == "value"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ttl(redis_client):
    """Test key expiration."""
    await redis_client.set("temp", "value", ttl=1)
    assert await redis_client.get("temp") == "value"

    await asyncio.sleep(2)
    assert await redis_client.get("temp") is None


@pytest.mark.integration
@pytest.mark.asyncio
async def test_distributed_lock(redis_client):
    """Test distributed locking."""
    from internal_cache import DistributedLock

    async with DistributedLock(
        client=redis_client,
        lock_name="test:lock",
        timeout=5,
    ) as acquired:
        assert acquired is True
```

## LocalStack (AWS Services)

### Complete Setup

```python
# tests/integration/test_aws/conftest.py

import pytest
import pytest_asyncio
from testcontainers.localstack import LocalStackContainer
from testcontainers.core.waiting_utils import wait_for_logs
from internal_aws import (
    S3Client, S3ClientConfig,
    DynamoTable, DynamoDBConfig,
    SQSClient, SQSConfig,
    ExplicitCredentialProvider,
)


@pytest.fixture(scope="session")
def localstack_container():
    """Start LocalStack with multiple AWS services."""
    localstack = LocalStackContainer(image="localstack/localstack:latest")
    localstack.with_services("s3", "dynamodb", "sqs")
    localstack.start()

    # Wait for LocalStack to be ready
    wait_for_logs(localstack, "Ready", timeout=60)

    yield localstack

    localstack.stop()


@pytest.fixture
def aws_credentials(localstack_container):
    """Create AWS credentials for LocalStack."""
    return ExplicitCredentialProvider(
        access_key_id="test",
        secret_access_key="test",
        region="us-east-1"
    )


@pytest.fixture
def s3_config(localstack_container):
    """S3 configuration from LocalStack."""
    return S3ClientConfig(
        bucket_name="test-bucket",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest_asyncio.fixture
async def s3_client(s3_config, aws_credentials):
    """S3 client with bucket creation."""
    client = S3Client(s3_config, aws_credentials)

    # Create bucket
    async with client.get_client() as s3:
        try:
            await s3.create_bucket(Bucket=s3_config.bucket_name)
        except Exception:
            pass

    yield client


@pytest.fixture
def dynamodb_config(localstack_container):
    """DynamoDB configuration from LocalStack."""
    return DynamoDBConfig(
        table_name="test-table",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest_asyncio.fixture
async def dynamodb_table(dynamodb_config, aws_credentials):
    """DynamoDB table with creation."""
    from pydantic import BaseModel

    class TestItem(BaseModel):
        id: str
        name: str

    table = DynamoTable(
        dynamodb_config,
        TestItem,
        aws_credentials,
        key_schema=[{"AttributeName": "id", "KeyType": "HASH"}],
        attribute_definitions=[{"AttributeName": "id", "AttributeType": "S"}]
    )

    # Create table
    try:
        await table.create_table()
    except Exception:
        pass

    yield table
```

### Example Tests

```python
# tests/integration/test_aws/test_s3.py

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_s3_put_get(s3_client):
    """Test S3 upload and download."""
    await s3_client.put_object("test.txt", b"Hello, World!")

    content = await s3_client.get_object_as_bytes("test.txt")
    assert content == b"Hello, World!"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_s3_json(s3_client):
    """Test S3 JSON operations."""
    data = {"key": "value"}

    import json
    await s3_client.put_object(
        "data.json",
        json.dumps(data),
        content_type="application/json"
    )

    retrieved = await s3_client.get_object_as_json("data.json")
    assert retrieved == data
```

## MongoDB

### Complete Setup

```python
# tests/integration/test_mongo/conftest.py

import pytest
import pytest_asyncio
from testcontainers.mongodb import MongoDbContainer
from motor.motor_asyncio import AsyncIOMotorClient


@pytest.fixture(scope="session")
def mongo_container():
    """Start MongoDB container for test session."""
    mongo = MongoDbContainer("mongo:7")
    mongo.start()

    yield mongo

    mongo.stop()


@pytest.fixture
def mongo_connection_string(mongo_container):
    """Get MongoDB connection string."""
    return mongo_container.get_connection_url()


@pytest_asyncio.fixture
async def mongo_client(mongo_connection_string):
    """Create MongoDB client with cleanup."""
    client = AsyncIOMotorClient(mongo_connection_string)

    yield client

    # Cleanup: drop test database
    await client.drop_database("test_db")
    client.close()


@pytest_asyncio.fixture
async def mongo_collection(mongo_client):
    """Get MongoDB collection for testing."""
    db = mongo_client.test_db
    collection = db.test_collection

    yield collection

    # Cleanup: clear collection
    await collection.delete_many({})
```

### Example Tests

```python
# tests/integration/test_mongo/test_database.py

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_insert_find(mongo_collection):
    """Test MongoDB insert and find."""
    doc = {"name": "test", "value": 42}
    result = await mongo_collection.insert_one(doc)

    found = await mongo_collection.find_one({"_id": result.inserted_id})
    assert found["name"] == "test"
    assert found["value"] == 42


@pytest.mark.integration
@pytest.mark.asyncio
async def test_update(mongo_collection):
    """Test MongoDB update."""
    doc = {"name": "original", "value": 1}
    result = await mongo_collection.insert_one(doc)

    await mongo_collection.update_one(
        {"_id": result.inserted_id},
        {"$set": {"value": 2}}
    )

    updated = await mongo_collection.find_one({"_id": result.inserted_id})
    assert updated["value"] == 2
```

## MySQL

### Complete Setup

```python
# tests/integration/test_mysql/conftest.py

import pytest
import pytest_asyncio
from testcontainers.mysql import MySqlContainer
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)


@pytest.fixture(scope="session")
def mysql_container():
    """Start MySQL container for test session."""
    mysql = MySqlContainer("mysql:8.0")
    mysql.start()

    yield mysql

    mysql.stop()


@pytest.fixture
def mysql_connection_string(mysql_container):
    """Get MySQL connection string for asyncio."""
    # Convert mysql:// to mysql+aiomysql://
    url = mysql_container.get_connection_url()
    return url.replace("mysql://", "mysql+aiomysql://")


@pytest_asyncio.fixture
async def mysql_session(mysql_connection_string):
    """Create MySQL session with table setup/cleanup."""
    engine = create_async_engine(mysql_connection_string)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Create session
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        yield session

    # Cleanup
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()
```

### Example Tests

```python
# tests/integration/test_mysql/test_database.py

import pytest
from sqlalchemy import select


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_user(mysql_session):
    """Test creating user in MySQL."""
    user = User(username="testuser", email="test@example.com")
    mysql_session.add(user)
    await mysql_session.commit()
    await mysql_session.refresh(user)

    assert user.id is not None
```

## Kafka

### Complete Setup

```python
# tests/integration/test_kafka/conftest.py

import pytest
import pytest_asyncio
from testcontainers.kafka import KafkaContainer
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer


@pytest.fixture(scope="session")
def kafka_container():
    """Start Kafka container for test session."""
    kafka = KafkaContainer()
    kafka.start()

    yield kafka

    kafka.stop()


@pytest.fixture
def kafka_bootstrap_servers(kafka_container):
    """Get Kafka bootstrap servers."""
    return kafka_container.get_bootstrap_server()


@pytest_asyncio.fixture
async def kafka_producer(kafka_bootstrap_servers):
    """Create Kafka producer."""
    producer = AIOKafkaProducer(
        bootstrap_servers=kafka_bootstrap_servers
    )
    await producer.start()

    yield producer

    await producer.stop()


@pytest_asyncio.fixture
async def kafka_consumer(kafka_bootstrap_servers):
    """Create Kafka consumer."""
    consumer = AIOKafkaConsumer(
        "test-topic",
        bootstrap_servers=kafka_bootstrap_servers,
        auto_offset_reset="earliest",
        group_id="test-group",
    )
    await consumer.start()

    yield consumer

    await consumer.stop()
```

### Example Tests

```python
# tests/integration/test_kafka/test_messaging.py

import pytest
import asyncio


@pytest.mark.integration
@pytest.mark.asyncio
async def test_produce_consume(kafka_producer, kafka_consumer):
    """Test Kafka produce and consume."""
    # Produce message
    await kafka_producer.send_and_wait(
        "test-topic",
        b"test message"
    )

    # Consume message
    async for msg in kafka_consumer:
        assert msg.value == b"test message"
        break  # Only consume one message
```

## ElasticSearch

### Complete Setup

```python
# tests/integration/test_elasticsearch/conftest.py

import pytest
import pytest_asyncio
from testcontainers.elasticsearch import ElasticSearchContainer
from elasticsearch import AsyncElasticsearch


@pytest.fixture(scope="session")
def elasticsearch_container():
    """Start ElasticSearch container for test session."""
    es = ElasticSearchContainer("elasticsearch:8.11.0")
    es.start()

    yield es

    es.stop()


@pytest.fixture
def elasticsearch_url(elasticsearch_container):
    """Get ElasticSearch URL."""
    return elasticsearch_container.get_url()


@pytest_asyncio.fixture
async def elasticsearch_client(elasticsearch_url):
    """Create ElasticSearch client with cleanup."""
    client = AsyncElasticsearch(
        [elasticsearch_url],
        verify_certs=False,
        ssl_show_warn=False
    )

    yield client

    # Cleanup: delete test indices
    try:
        await client.indices.delete(index="test-*")
    except Exception:
        pass

    await client.close()
```

### Example Tests

```python
# tests/integration/test_elasticsearch/test_search.py

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_index_search(elasticsearch_client):
    """Test ElasticSearch indexing and search."""
    # Index document
    await elasticsearch_client.index(
        index="test-index",
        id="1",
        document={"title": "Test", "content": "Hello"}
    )

    # Refresh index
    await elasticsearch_client.indices.refresh(index="test-index")

    # Search
    result = await elasticsearch_client.search(
        index="test-index",
        query={"match": {"title": "Test"}}
    )

    assert result["hits"]["total"]["value"] == 1
```
