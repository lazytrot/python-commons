# Testcontainer Testing Patterns

## Core Principles

1. **No Mocking** - Test against real services, not mocks
2. **Container Reuse** - Use session-scoped fixtures to share containers across tests
3. **Fast Feedback** - Balance speed with realism (SQLite for unit, containers for integration)
4. **Proper Cleanup** - Always clean data between tests, stop containers after session

## Fixture Scopes

### Session Scope (Recommended for Containers)

**When to use:** Container startup/shutdown is expensive. Share one container across all tests.

```python
@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container once for entire test session."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    yield redis

    redis.stop()
```

**Benefits:**
- Fast test execution (container starts once)
- Resource efficient
- Mirrors production (long-running services)

**Considerations:**
- Must clean data between tests (use function-scoped client fixtures)
- Test isolation requires explicit cleanup

### Module Scope

**When to use:** Tests in one file need different container configuration than other files.

```python
@pytest.fixture(scope="module")
def postgres_container():
    """Start PostgreSQL container for this test module."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres
```

**Benefits:**
- Isolated per test file
- Good for different configurations per module

**Trade-off:**
- Slower than session scope (restarts per module)
- Faster than function scope

### Function Scope (For Clients, Not Containers)

**When to use:** Individual test needs isolated client or data.

```python
@pytest.fixture  # function scope is default
async def redis_client(redis_config):
    """Create fresh Redis client for each test."""
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database
    await client.client.flushdb()
    await client.close()
```

**Benefits:**
- Perfect test isolation
- Each test gets clean state

**Anti-pattern:**
- ❌ Don't use function scope for containers (too slow)

## Configuration Extraction Pattern

**Pattern:** Extract connection details from container to create config objects.

```python
@pytest.fixture(scope="session")
def redis_container():
    """Start container."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    yield redis
    redis.stop()


@pytest.fixture
def redis_config(redis_container):
    """Extract config from container."""
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
        ssl=False,
    )


@pytest.fixture
async def redis_client(redis_config):
    """Create client from config."""
    client = RedisClient(redis_config)
    await client.connect()
    yield client
    await client.client.flushdb()
    await client.close()
```

**Why this pattern:**
- ✅ Container is session-scoped (fast)
- ✅ Config is function-scoped (can be customized per test)
- ✅ Client is function-scoped (clean state per test)
- ✅ Separation of concerns (container ≠ config ≠ client)

## Cleanup Strategies

### Strategy 1: Flush Database (Fast)

```python
@pytest.fixture
async def redis_client(redis_config):
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Fast cleanup: flush all data
    await client.client.flushdb()
    await client.close()
```

**Use for:** Redis, caches, key-value stores

### Strategy 2: Drop/Recreate Tables

```python
@pytest.fixture
async def db_session(postgres_config):
    db_manager = DatabaseSessionManager(postgres_config)

    # Create tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db_manager() as session:
        yield session

    # Cleanup: drop tables
    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await db_manager.close()
```

**Use for:** SQL databases with schema management

### Strategy 3: Delete Resources

```python
@pytest_asyncio.fixture
async def s3_client(s3_config, aws_credentials):
    client = S3Client(s3_config, aws_credentials)

    # Create bucket
    async with client.get_client() as s3:
        try:
            await s3.create_bucket(Bucket=s3_config.bucket_name)
        except Exception:
            pass

    yield client

    # Cleanup: delete all objects
    # (bucket deletion happens when container stops)
```

**Use for:** Object stores, message queues

## LocalStack Multi-Service Pattern

**Pattern:** One LocalStack container supports multiple AWS services.

```python
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
def s3_config(localstack_container):
    """S3 configuration from LocalStack."""
    return S3ClientConfig(
        bucket_name="test-bucket",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest.fixture
def dynamodb_config(localstack_container):
    """DynamoDB configuration from LocalStack."""
    return DynamoDBConfig(
        table_name="test-table",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )
```

**Benefits:**
- ✅ One container for all AWS services
- ✅ Fast startup (single container)
- ✅ Realistic AWS API behavior

## Common Pitfalls

### ❌ Anti-Pattern: Mocking with Testcontainers

```python
# DON'T DO THIS
@pytest.fixture
def mock_redis():
    return MagicMock()  # ❌ Defeats the purpose of testcontainers
```

**Why wrong:** Testcontainers exist to test against real services. Mocking defeats the purpose.

### ❌ Anti-Pattern: Function-Scoped Containers

```python
# DON'T DO THIS
@pytest.fixture  # function scope - restarts for EVERY test
def redis_container():
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    yield redis
    redis.stop()
```

**Why wrong:** Extremely slow. Container restarts for every test.

### ❌ Anti-Pattern: No Cleanup

```python
# DON'T DO THIS
@pytest.fixture
async def redis_client(redis_config):
    client = RedisClient(redis_config)
    await client.connect()
    yield client
    # ❌ No cleanup - data leaks between tests
```

**Why wrong:** Tests contaminate each other with leftover data.

### ❌ Anti-Pattern: Manual Container Management in Tests

```python
# DON'T DO THIS
def test_redis():
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    # ... test code ...
    redis.stop()  # ❌ Duplicates fixture logic
```

**Why wrong:** Use fixtures for container management, not manual start/stop in tests.

## Performance Optimization

### Use SQLite for Unit Tests

```python
# conftest.py

@pytest.fixture
def sqlite_memory_config():
    """Fast SQLite in-memory for unit tests."""
    return DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)


@pytest_asyncio.fixture
async def sqlite_session(sqlite_memory_config):
    """Fast in-memory session for unit tests."""
    db_manager = DatabaseSessionManager(sqlite_memory_config)

    async with db_manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with db_manager() as session:
        yield session

    await db_manager.close()
```

### Session-Scoped Containers

```python
# Slow: 10 tests × 2 seconds = 20 seconds
@pytest.fixture  # function scope
def postgres_container():
    with PostgresContainer() as postgres:
        yield postgres

# Fast: 1 × 2 seconds = 2 seconds
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer() as postgres:
        yield postgres
```

## Async/Await Patterns

### Use pytest-asyncio

```python
import pytest_asyncio

@pytest_asyncio.fixture
async def redis_client(redis_config):
    """Async fixture for async client."""
    client = RedisClient(redis_config)
    await client.connect()
    yield client
    await client.close()


@pytest.mark.asyncio
async def test_redis_operations(redis_client):
    """Async test using async client."""
    await redis_client.set("key", "value")
    result = await redis_client.get("key")
    assert result == "value"
```

### Mixing Sync and Async

```python
@pytest.fixture(scope="session")
def redis_container():
    """Sync fixture for container."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    yield redis
    redis.stop()


@pytest_asyncio.fixture
async def redis_client(redis_container):  # Can use sync fixture
    """Async fixture using sync container fixture."""
    config = RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
    )
    client = RedisClient(config)
    await client.connect()
    yield client
    await client.close()
```

## Test Organization

```
tests/
├── conftest.py                    # Shared fixtures
├── unit/                          # Fast SQLite tests
│   ├── conftest.py               # SQLite fixtures
│   └── test_business_logic.py
└── integration/                   # Real service tests
    ├── conftest.py               # Testcontainer fixtures
    ├── test_redis/
    │   ├── conftest.py           # Redis-specific fixtures
    │   └── test_cache.py
    ├── test_postgres/
    │   ├── conftest.py           # Postgres-specific fixtures
    │   └── test_database.py
    └── test_aws/
        ├── conftest.py           # LocalStack fixtures
        └── test_s3.py
```

**Pattern:**
- Top-level `conftest.py` - shared fixtures across all tests
- `unit/conftest.py` - SQLite and fast fixtures
- `integration/conftest.py` - testcontainer fixtures
- Service-specific `conftest.py` - service-specific setup
