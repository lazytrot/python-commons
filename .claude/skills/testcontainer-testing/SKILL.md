---
name: testcontainer-testing
description: This skill should be used when writing integration tests for services like databases (PostgreSQL, MySQL, MongoDB), caches (Redis), message queues (Kafka, SQS), or cloud services (AWS via LocalStack). Use when asked to test against real infrastructure, set up testcontainers, optimize slow integration tests through container reuse, or avoid mocking in favor of real service testing.
---

# Testcontainer Testing

## Overview

Write integration tests against real services using testcontainers with proper container reuse patterns. This skill provides proven patterns for testing databases, caches, message queues, and cloud services without mocking, achieving both realistic testing and fast execution through session-scoped container fixtures.

## When to Use This Skill

Activate this skill when the user requests:

- "Write integration tests for [PostgreSQL/Redis/MongoDB/etc.]"
- "Set up testcontainers for my [service] tests"
- "Test my [database/cache] code against a real instance"
- "My integration tests are slow, containers keep restarting"
- "How do I test AWS services without mocking?"
- "I need to avoid mocking and test real infrastructure"

## Core Principles

Follow these principles when writing testcontainer-based tests:

1. **No Mocking** - Test against real services, not mocks. Testcontainers exist to provide realistic infrastructure.

2. **Container Reuse** - Use session-scoped fixtures for containers, function-scoped fixtures for clients/sessions.

3. **Fast Feedback** - Balance speed with realism:
   - Unit tests: SQLite in-memory (milliseconds)
   - Integration tests: Testcontainers (seconds)

4. **Proper Cleanup** - Clean data between tests, not containers. Stop containers only after session ends.

## Quick Start

### 1. Choose Your Service

Identify which service needs testing:
- **Databases**: PostgreSQL, MySQL, MongoDB
- **Caches**: Redis
- **Cloud Services**: LocalStack (S3, DynamoDB, SQS)
- **Message Queues**: Kafka, RabbitMQ
- **Search**: ElasticSearch

### 2. Use the Template

Copy the appropriate template from `assets/templates/`:
- `conftest_postgres.py` - PostgreSQL setup
- `conftest_redis.py` - Redis setup
- `conftest_localstack.py` - AWS services (S3, DynamoDB, SQS)
- `test_example.py` - Example test structure

### 3. Customize the Fixture

Replace TODOs in the template:
- Model definitions (for databases)
- Table/bucket/queue names
- Service-specific configuration

### 4. Write Tests

Follow the pattern in `test_example.py`:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_your_feature(service_client):
    # Your test code using the client fixture
    pass
```

## The Three-Fixture Pattern

**Best Practice:** Use three levels of fixtures for optimal performance and isolation.

### Level 1: Container Fixture (Session Scope)

```python
@pytest.fixture(scope="session")
def redis_container():
    """Start container ONCE for entire test session."""
    redis = RedisContainer("redis:7-alpine")
    redis.start()

    yield redis

    redis.stop()
```

**Why session scope:** Container startup is expensive (2-10 seconds). Share one container across all tests.

### Level 2: Config Fixture (Function Scope)

```python
@pytest.fixture
def redis_config(redis_container):
    """Extract config from container."""
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
    )
```

**Why function scope:** Allows per-test customization (different db numbers, settings).

### Level 3: Client Fixture (Function Scope)

```python
@pytest_asyncio.fixture
async def redis_client(redis_config):
    """Create client with cleanup."""
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database
    await client.client.flushdb()
    await client.close()
```

**Why function scope:** Each test gets clean state. Cleanup happens automatically.

## Cleanup Strategies

Choose the right cleanup strategy for your service:

### Redis/Caches: Flush Database

```python
await client.client.flushdb()  # Fast, clears all data
```

### SQL Databases: Drop/Create Tables

```python
async with manager.engine.begin() as conn:
    await conn.run_sync(Base.metadata.drop_all)
```

### Object Stores: Delete Resources

```python
# Delete objects (LocalStack cleanup handles buckets)
async with client.get_client() as s3:
    # Delete logic if needed
```

**Key Rule:** Clean data between tests, not containers. Container recreation is too slow.

## Common Services

### PostgreSQL

```python
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture
def postgres_config(postgres_container):
    return DatabaseConfig(
        driver=DatabaseDriver.POSTGRESQL,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
    )

@pytest_asyncio.fixture
async def db_session(postgres_config):
    manager = DatabaseSessionManager(postgres_config)

    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager() as session:
        yield session

    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await manager.close()
```

### Redis

```python
@pytest.fixture(scope="session")
def redis_container():
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    yield redis
    redis.stop()

@pytest.fixture
def redis_config(redis_container):
    return RedisConfig(
        host=redis_container.get_container_host_ip(),
        port=int(redis_container.get_exposed_port(6379)),
        db=0,
    )

@pytest_asyncio.fixture
async def redis_client(redis_config):
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    await client.client.flushdb()
    await client.close()
```

### LocalStack (AWS Services)

```python
@pytest.fixture(scope="session")
def localstack_container():
    localstack = LocalStackContainer(image="localstack/localstack:latest")
    localstack.with_services("s3", "dynamodb", "sqs")
    localstack.start()

    wait_for_logs(localstack, "Ready", timeout=60)

    yield localstack

    localstack.stop()

@pytest.fixture
def s3_config(localstack_container):
    return S3ClientConfig(
        bucket_name="test-bucket",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )

@pytest_asyncio.fixture
async def s3_client(s3_config, aws_credentials):
    client = S3Client(s3_config, aws_credentials)

    async with client.get_client() as s3:
        await s3.create_bucket(Bucket=s3_config.bucket_name)

    yield client
```

## Anti-Patterns to Avoid

### ❌ Function-Scoped Containers

```python
# DON'T DO THIS - Too slow
@pytest.fixture  # function scope
def redis_container():
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    yield redis
    redis.stop()
```

**Fix:** Use `scope="session"` for containers.

### ❌ Mocking with Testcontainers

```python
# DON'T DO THIS - Defeats the purpose
@pytest.fixture
def mock_redis():
    return MagicMock()
```

**Fix:** Use real containers. That's why testcontainers exist.

### ❌ No Cleanup

```python
# DON'T DO THIS - Tests contaminate each other
@pytest.fixture
async def redis_client(redis_config):
    client = RedisClient(redis_config)
    await client.connect()
    yield client
    # Missing cleanup!
```

**Fix:** Always clean data in teardown.

### ❌ Manual Container Management

```python
# DON'T DO THIS - Use fixtures instead
def test_redis():
    redis = RedisContainer("redis:7-alpine")
    redis.start()
    # test code
    redis.stop()
```

**Fix:** Use fixtures for all container lifecycle management.

## Performance Tips

### Use SQLite for Unit Tests

```python
@pytest.fixture
def sqlite_memory_config():
    """Fast in-memory SQLite for unit tests."""
    return DatabaseConfig(driver=DatabaseDriver.SQLITE_MEMORY)
```

**Speed:** SQLite in-memory = milliseconds, PostgreSQL testcontainer = seconds.

**Strategy:** Unit tests use SQLite, integration tests use real databases.

### Session-Scoped Containers

```python
# Slow: 10 tests × 2 seconds = 20 seconds
@pytest.fixture  # function scope
def postgres_container():
    with PostgresContainer() as postgres:
        yield postgres

# Fast: 1 × 2 seconds = 2 seconds for all tests
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer() as postgres:
        yield postgres
```

### Share LocalStack Across Services

```python
# One container for all AWS services
localstack.with_services("s3", "dynamodb", "sqs")
```

**Why:** Faster than starting separate containers for each service.

## Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── unit/                    # Fast tests (SQLite)
│   ├── conftest.py
│   └── test_*.py
└── integration/             # Real services
    ├── conftest.py          # Testcontainer fixtures
    ├── test_redis/
    │   ├── conftest.py      # Redis-specific
    │   └── test_cache.py
    ├── test_postgres/
    │   ├── conftest.py      # Postgres-specific
    │   └── test_database.py
    └── test_aws/
        ├── conftest.py      # LocalStack fixtures
        └── test_s3.py
```

## Resources

### references/patterns.md
Comprehensive patterns and best practices:
- Fixture scope decision making
- Cleanup strategies for different services
- LocalStack multi-service patterns
- Common pitfalls and solutions
- Async/await patterns

**Read when:** Need deep understanding of patterns, troubleshooting issues, or optimizing test performance.

### references/services.md
Complete, copy-paste examples for:
- PostgreSQL, MySQL
- Redis
- MongoDB
- LocalStack (S3, DynamoDB, SQS)
- Kafka
- ElasticSearch

**Read when:** Setting up a specific service for the first time or need complete working example.

### assets/templates/
Ready-to-use templates:
- `conftest_postgres.py` - PostgreSQL fixture template
- `conftest_redis.py` - Redis fixture template
- `conftest_localstack.py` - LocalStack/AWS template
- `test_example.py` - Test structure examples

**Use when:** Starting new integration tests. Copy, customize TODOs, and use immediately.

## Workflow

**Step 1:** Identify service type (database, cache, AWS, etc.)

**Step 2:** Copy appropriate template from `assets/templates/`

**Step 3:** Customize TODOs:
- Model definitions
- Service names (tables, buckets, queues)
- Configuration parameters

**Step 4:** Verify fixture scopes:
- Container: `scope="session"` ✓
- Config: function scope (default) ✓
- Client: function scope with cleanup ✓

**Step 5:** Write tests using the fixtures

**Step 6:** Run and verify:
- Tests pass ✓
- Containers start once ✓
- Tests are isolated ✓

**Reference `references/patterns.md` for advanced patterns.**

**Reference `references/services.md` for service-specific examples.**
