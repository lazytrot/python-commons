---
name: testcontainer-testing
description: This skill should be used when writing END-TO-END service tests that validate entire applications/services work correctly with real infrastructure. Test complete APIs, workflows, and service behavior against real databases (PostgreSQL, MySQL, MongoDB), caches (Redis), message queues (Kafka, SQS), and cloud services (AWS via LocalStack). Use for API-level tests, service integration tests, and end-to-end testing that ensures code doesn't break in production. Provides real infrastructure via Docker containers to catch bugs that mocks miss. NOT for isolated unit tests.
---

# Testcontainer Testing

## Overview

This skill transforms how you write end-to-end service tests. Instead of mocking infrastructure, you'll test your **entire application/service** against real databases, caches, and cloud services using Docker containers - ensuring your code doesn't break in production.

**Real Results:**
- python-commons repository: 336 tests, 82.95% coverage, 0 flaky tests, 0 mocking
- End-to-end tests run in seconds, not minutes
- Containers shared across entire test suite (PostgreSQL starts once for 50+ tests)
- Zero mock behavior - every test validates real infrastructure behavior
- **Catches bugs that mocks miss** - validates actual service interactions

**This skill provides battle-tested patterns from production codebases.**

## When to Use This Skill

**Use testcontainers for END-TO-END service testing** - testing that your entire application/service works correctly with real infrastructure. This ensures code doesn't break in production.

Activate this skill when the user requests:

- "Write end-to-end tests for my API/service"
- "Test my entire application against real infrastructure"
- "Write API-level tests that hit real databases"
- "Test complete workflows with real Redis/PostgreSQL/SQS"
- "Ensure my service doesn't break in production"
- "Write integration tests without mocking"
- "My integration tests are slow, containers keep restarting"
- "Test AWS integrations without mocking"

**NOT for:** Isolated unit tests of pure business logic (use mocks/in-memory for those)

## Test Level Guidance

**Unit Tests (No Testcontainers):**
- Test isolated business logic
- Pure functions, calculations, validations
- Use mocks for external dependencies
- Run in milliseconds
- Example: Testing a discount calculation function

**End-to-End Service Tests (Use Testcontainers):**
- Test entire application/service with real infrastructure
- API endpoints → business logic → database/cache/queue
- Complete workflows from request to response
- Validates actual service behavior
- Run in seconds
- Examples:
  - Testing API endpoint that creates user, saves to PostgreSQL, publishes to SQS
  - Testing cache invalidation workflow with Redis
  - Testing HTTP client retry behavior with MockServer
  - Testing S3 upload/download with LocalStack

**Full System Tests (May Use Testcontainers):**
- Test multiple services together
- Cross-service communication
- May use docker-compose or Kubernetes
- Run in minutes

**Testcontainers are for testing that your service/application works end-to-end with real infrastructure.**

## Core Principles

Follow these principles when writing end-to-end testcontainer-based tests:

1. **No Mocking Infrastructure** - Test against real databases, caches, queues, cloud services. Testcontainers provide real infrastructure to catch bugs mocks miss.

2. **Test Complete Workflows** - Test your application from API/entry point through business logic to data persistence and external services.

3. **Container Reuse** - Use session-scoped fixtures for containers, function-scoped fixtures for clients/sessions.

4. **Fast Feedback** - Balance speed with realism:
   - Unit tests: Isolated logic with mocks (milliseconds)
   - End-to-end service tests: Testcontainers (seconds)
   - Full system tests: Multiple services (minutes)

5. **Proper Cleanup** - Clean data between tests, not containers. Stop containers only after session ends.

6. **Catch Production Bugs** - Validate that code works with real service behavior, connection handling, timeouts, retries, error cases.

## Quick Start

**Three steps to start testing:**

1. **Set up fixtures** - Use three-fixture pattern: Container (session) → Config (function) → Client (function + cleanup)
2. **Write tests** - Test complete workflows with real infrastructure
3. **See Complete Working Examples section** - Copy patterns for PostgreSQL, Redis, LocalStack, MockServer, or API testing

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

## Condition-Based Waiting Patterns

**Critical Pattern:** Eliminate flaky tests by waiting for actual conditions instead of arbitrary sleeps.

### The Problem with Sleep

```python
# ❌ FLAKY: Timing guess
await asyncio.sleep(2)  # Hope service is ready
result = await service.get_status()
```

**Why this fails:**
- CI/CD environments slower than dev machines
- Timing varies across systems
- Too short = flaky failures
- Too long = slow tests

### The Solution: Poll for Conditions

```python
# ✅ RELIABLE: Wait for actual condition
from tests.test_utils import wait_for_condition

await wait_for_condition(
    lambda: service.is_ready(),
    "service to be ready",
    timeout_ms=5000
)
```

### Implementing wait_for_condition

**Create:** `tests/test_utils/wait.py`

```python
import asyncio
from typing import Callable, Any, TypeVar

T = TypeVar("T")


async def wait_for_condition(
    condition: Callable[[], Any],
    description: str,
    timeout_ms: int = 5000,
    poll_interval_ms: int = 10,
) -> Any:
    """
    Wait for a condition to become truthy.

    Args:
        condition: Callable that returns truthy value when condition is met (can be async)
        description: Human-readable description for error messages
        timeout_ms: Maximum time to wait in milliseconds
        poll_interval_ms: How often to check condition in milliseconds

    Returns:
        The truthy value returned by condition

    Raises:
        TimeoutError: If condition not met within timeout

    Example:
        await wait_for_condition(
            lambda: len(messages) > 0,
            "messages to be received",
            timeout_ms=3000
        )
    """
    start_time = asyncio.get_event_loop().time()
    timeout_seconds = timeout_ms / 1000
    poll_interval_seconds = poll_interval_ms / 1000

    while True:
        result = condition()
        # Handle both sync and async conditions
        if asyncio.iscoroutine(result):
            result = await result

        if result:
            return result

        elapsed = asyncio.get_event_loop().time() - start_time
        if elapsed > timeout_seconds:
            raise TimeoutError(
                f"Timeout waiting for {description} after {timeout_ms}ms"
            )

        await asyncio.sleep(poll_interval_seconds)
```

### Common Waiting Patterns

#### Wait for Container Readiness

```python
# MockServer example
def mock_server_url(mockserver_container):
    """Get MockServer URL and wait for it to be ready."""
    import requests, time

    host = mockserver_container.get_container_host_ip()
    port = mockserver_container.get_exposed_port(1080)
    url = f"http://{host}:{port}"

    # Wait for MockServer to be ready (simpler sync version)
    for _ in range(30):  # Try for 30 seconds
        try:
            response = requests.put(f"{url}/status", timeout=1.0)
            break  # Any response means server is up
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(1)
    else:
        raise RuntimeError("MockServer failed to start")

    return url

# Using wait_for_condition (async version)
async def async_check_mockserver(url):
    """Async readiness check."""
    import httpx

    async def check_ready():
        try:
            async with httpx.AsyncClient() as client:
                response = await client.put(f"{url}/status", timeout=1.0)
                return response.status_code in [200, 404]  # Any response is OK
        except (httpx.ConnectError, httpx.TimeoutException):
            return False

    await wait_for_condition(
        check_ready,
        "MockServer container to be ready",
        timeout_ms=30000  # 30 seconds
    )
```

#### Wait for Redis Key Expiry

```python
async def wait_for_ttl_expiry(
    redis_client,
    key: str,
    timeout_ms: int = 5000,
) -> bool:
    """Wait for a Redis key's TTL to expire (key to be deleted)."""
    async def check_deleted():
        exists = await redis_client.exists(key)
        return exists == 0

    await wait_for_condition(
        check_deleted,
        f"Redis key '{key}' to be deleted",
        timeout_ms=timeout_ms,
    )
    return True
```

#### Wait for Lock Renewal

```python
async def wait_for_lock_renewal(
    redis_client,
    lock_key: str,
    initial_ttl: int,
    timeout_ms: int = 5000,
) -> bool:
    """Wait for a distributed lock to be renewed (TTL refreshed)."""
    async def check_renewed():
        current_ttl = await redis_client.ttl(lock_key)
        # TTL was refreshed if it's greater than initial (accounting for time passed)
        return current_ttl > initial_ttl - 1

    await wait_for_condition(
        check_renewed,
        f"lock '{lock_key}' to be renewed",
        timeout_ms=timeout_ms,
    )
    return True
```

#### Wait for Message Processing

```python
# Real example from SQS consumer tests
processed = []

async def handler(message):
    processed.append(message["Body"])

consumer = SQSConsumer(...)
task = asyncio.create_task(consumer.start())

# Wait for consumer to process messages
await wait_for_condition(
    lambda: len(processed) > 0,
    "consumer to process messages",
    timeout_ms=5000
)

await consumer.stop()
```

### Anti-Pattern: Mixing Sleep and Polling

```python
# ❌ DON'T DO THIS
for _ in range(30):
    if condition():
        break
    time.sleep(1)  # Wastes full second even if condition met after 10ms
```

**Fix:** Use `wait_for_condition` with short poll_interval_ms (default 10ms).

```python
# ✅ DO THIS
await wait_for_condition(
    condition,
    "condition to be met",
    timeout_ms=30000,
    poll_interval_ms=10  # Check every 10ms
)
```

### When to Use

**Use condition-based waiting when:**
- Waiting for container startup/readiness
- Testing asynchronous operations (message processing, background tasks)
- Testing TTL/expiry behavior
- Testing distributed locks
- Any test that currently uses `time.sleep()` or `asyncio.sleep()`

**Benefits:**
- ✅ Tests fail fast (no waiting full timeout on genuine failures)
- ✅ Tests pass quickly (stops immediately when condition met)
- ✅ Eliminates race conditions
- ✅ Clear failure messages ("Timeout waiting for X after Yms")

## Supported Services

**See "Complete Working Examples" section for copy-paste fixtures:**
- **PostgreSQL** - Relational database with SQLAlchemy
- **Redis** - Cache, distributed locks, pub/sub
- **LocalStack** - AWS services (S3, DynamoDB, SQS)
- **MockServer** - HTTP client testing with controlled responses
- **API Testing** - FastAPI with multiple infrastructure components

## Multi-Container Test Suites

**Pattern:** Share multiple containers across entire test suite for maximum efficiency.

### Root-Level Shared Fixtures

**File:** `tests/conftest.py`

```python
"""
Shared pytest fixtures for integration tests.

Uses testcontainers and LocalStack for real service testing.
Avoids mocking - tests against actual infrastructure.
"""

import pytest
import pytest_asyncio

try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    from internal_rdbms import DatabaseConfig
    from internal_cache import RedisClient, RedisConfig
    HAS_INTEGRATION_DEPS = True
except ImportError:
    HAS_INTEGRATION_DEPS = False


# Only define fixtures if integration dependencies are available
if HAS_INTEGRATION_DEPS:
    # PostgreSQL fixtures

    @pytest.fixture(scope="session")
    def postgres_container():
        """Start PostgreSQL container for the test session."""
        with PostgresContainer("postgres:15-alpine") as postgres:
            yield postgres


    @pytest.fixture
    def postgres_config(postgres_container):
        """Create PostgreSQL configuration from test container."""
        return DatabaseConfig(
            driver="postgresql+asyncpg",
            host=postgres_container.get_container_host_ip(),
            port=int(postgres_container.get_exposed_port(5432)),
            user=postgres_container.username,
            password=postgres_container.password,
            name=postgres_container.dbname,
            echo=True,
        )


    # Redis fixtures

    @pytest.fixture(scope="session")
    def redis_container():
        """Start Redis container for the test session."""
        with RedisContainer("redis:7-alpine") as redis:
            yield redis


    @pytest.fixture
    def redis_config(redis_container):
        """Create Redis configuration from test container."""
        return RedisConfig(
            host=redis_container.get_container_host_ip(),
            port=int(redis_container.get_exposed_port(6379)),
            db=0,
        )


    @pytest_asyncio.fixture
    async def redis_client(redis_config):
        """
        Provide Redis client connected to real Redis container.

        No mocking - tests against actual Redis instance.
        """
        client = RedisClient(redis_config)
        await client.connect()

        yield client

        # Cleanup: flush database
        await client.client.flushdb()
        await client.close()
```

### Service-Specific Fixtures

**File:** `tests/integration/test_internal_aws/conftest.py`

```python
"""Fixtures for internal_aws integration tests."""

import pytest
import pytest_asyncio
from testcontainers.localstack import LocalStackContainer
from testcontainers.core.waiting_utils import wait_for_logs

from internal_aws import (
    S3Client, S3ClientConfig,
    DynamoTable, DynamoDBConfig,
    SQSClient, SQSConfig,
    ExplicitCredentialProvider
)


@pytest.fixture(scope="session")
def localstack_container():
    """Start LocalStack container for AWS services."""
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
    """S3 client configuration for LocalStack."""
    return S3ClientConfig(
        bucket_name="test-bucket",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest.fixture
def dynamodb_config(localstack_container):
    """DynamoDB configuration for LocalStack."""
    return DynamoDBConfig(
        table_name="test-table",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest.fixture
def sqs_config(localstack_container):
    """SQS configuration for LocalStack."""
    # Create queue first
    import boto3
    sqs = boto3.client(
        "sqs",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    response = sqs.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]

    return SQSConfig(
        queue_url=queue_url,
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest_asyncio.fixture
async def s3_client(s3_config, aws_credentials):
    """S3 client connected to LocalStack."""
    client = S3Client(s3_config, aws_credentials)

    # Create bucket
    async with client.get_client() as s3:
        try:
            await s3.create_bucket(Bucket=s3_config.bucket_name)
        except Exception:
            pass  # Bucket might already exist

    yield client


@pytest_asyncio.fixture
async def sqs_client(sqs_config, aws_credentials):
    """SQS client connected to LocalStack."""
    client = SQSClient(sqs_config, aws_credentials)
    yield client
```

### Multi-Container Architecture

```
tests/
├── conftest.py                       # SESSION-SCOPED containers (shared)
│   ├── postgres_container            # Starts ONCE for ALL tests
│   ├── redis_container               # Starts ONCE for ALL tests
│   ├── postgres_config               # Function-scoped (per-test config)
│   └── redis_client                  # Function-scoped (per-test client + cleanup)
│
├── integration/
│   ├── test_internal_aws/
│   │   ├── conftest.py               # AWS-specific fixtures
│   │   │   ├── localstack_container  # SESSION-SCOPED (3 services in 1)
│   │   │   ├── s3_config             # Function-scoped
│   │   │   ├── dynamodb_config       # Function-scoped
│   │   │   ├── sqs_config            # Function-scoped
│   │   │   └── s3_client             # Function-scoped with cleanup
│   │   ├── test_s3.py                # Uses s3_client
│   │   ├── test_dynamodb.py          # Uses dynamodb fixtures
│   │   └── test_sqs.py               # Uses sqs_client
│   │
│   ├── test_internal_cache/
│   │   ├── test_locks.py             # Uses redis_client from root conftest
│   │   └── test_cache.py             # Uses redis_client from root conftest
│   │
│   └── test_internal_rdbms/
│       └── test_databases.py         # Uses postgres_config from root conftest
```

### Benefits of Multi-Container Pattern

**Performance:**
- PostgreSQL: Starts once (~3s), used by 50+ tests
- Redis: Starts once (~2s), used by 30+ tests
- LocalStack: Starts once (~10s), provides 3 AWS services to 40+ tests

**Total saved:** ~15 seconds per container × number of tests = minutes to hours

**Isolation:**
- Each test gets fresh client (function-scoped)
- Cleanup happens automatically after each test
- Containers are shared, data is isolated

**Realism:**
- Tests run against actual services
- Zero mocking
- Catches real integration bugs

### Import Guard Pattern

```python
try:
    from testcontainers.postgres import PostgresContainer
    from testcontainers.redis import RedisContainer
    HAS_INTEGRATION_DEPS = True
except ImportError:
    HAS_INTEGRATION_DEPS = False


if HAS_INTEGRATION_DEPS:
    # Define fixtures here
```

**Why:** Allows unit tests to run without Docker/testcontainers installed.

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

## Container Versioning Best Practices

**Critical:** Pin container versions for reproducible tests.

### Version Pinning Strategies

#### Strategy 1: Pin to Exact Version (Recommended)

```python
@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container - PINNED VERSION."""
    with PostgresContainer("postgres:15.4-alpine") as postgres:
        yield postgres
```

**Benefits:**
- ✅ Reproducible builds
- ✅ No surprise breakage from upstream changes
- ✅ Explicit version upgrade decisions

**When to use:** Production test suites, CI/CD pipelines

#### Strategy 2: Pin to Major Version

```python
@pytest.fixture(scope="session")
def redis_container():
    """Start Redis container - MAJOR VERSION PINNED."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis
```

**Benefits:**
- ✅ Get security patches automatically
- ✅ Stay within same major version
- ✅ Balance stability with updates

**When to use:** Development, when you want patch updates

#### Strategy 3: Latest Tag (Not Recommended)

```python
# ❌ DON'T DO THIS IN PRODUCTION
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:latest") as postgres:  # ❌ Unpredictable
        yield postgres
```

**Problems:**
- ❌ Tests break randomly when new version released
- ❌ Irreproducible builds
- ❌ Hard to debug version-specific issues

**When acceptable:** Quick prototyping only

### Recommended Container Versions

**Databases:**
```python
PostgresContainer("postgres:15.4-alpine")  # PostgreSQL 15.4
PostgresContainer("postgres:16.0-alpine")  # PostgreSQL 16.0
```

**Caches:**
```python
RedisContainer("redis:7.2-alpine")  # Redis 7.2
RedisContainer("redis:7-alpine")    # Redis 7.x (latest patch)
```

**AWS Services:**
```python
LocalStackContainer(image="localstack/localstack:3.0.2")  # LocalStack 3.0.2
LocalStackContainer(image="localstack/localstack:latest") # ⚠️ Use with caution
```

**HTTP Testing:**
```python
DockerContainer("mockserver/mockserver:5.15.0")     # MockServer 5.15.0
DockerContainer("mockserver/mockserver:latest")     # MockServer latest (stable)
```

**Message Queues:**
```python
DockerContainer("confluentinc/cp-kafka:7.5.0")  # Kafka 7.5.0
```

### Version Documentation Pattern

```python
@pytest.fixture(scope="session")
def postgres_container():
    """
    Start PostgreSQL container for testing.

    Version: postgres:15.4-alpine
    - PostgreSQL 15.4
    - Alpine Linux base (smaller image)
    - Updated: 2024-01-15
    - Reason: Stable release with security patches
    """
    with PostgresContainer("postgres:15.4-alpine") as postgres:
        yield postgres
```

**Include:**
- Exact version string
- Update date
- Reason for version choice
- Breaking changes if upgrading

### Version Upgrade Checklist

When upgrading container versions:

☐ Check container changelog for breaking changes
☐ Update version in fixture
☐ Update version in docstring
☐ Run full test suite locally
☐ Run test suite in CI
☐ Check for deprecation warnings
☐ Update any version-specific workarounds
☐ Document upgrade in commit message

### CI/CD Version Locking

**GitHub Actions example:**

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    env:
      # Lock container versions in CI
      POSTGRES_VERSION: "15.4-alpine"
      REDIS_VERSION: "7.2-alpine"
      LOCALSTACK_VERSION: "3.0.2"

    steps:
      - uses: actions/checkout@v4
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Run tests
        run: |
          pytest tests/ -v
```

### Image Size Optimization

**Use Alpine variants when available:**

```python
# Larger image (~300MB)
PostgresContainer("postgres:15.4")

# Smaller image (~200MB)
PostgresContainer("postgres:15.4-alpine")  # ✅ Recommended
```

**Benefits:**
- ✅ Faster pull times
- ✅ Less disk space
- ✅ Faster container startup

**Trade-offs:**
- Alpine uses musl libc instead of glibc
- Rare compatibility issues (usually not a problem)

### Version Matrix Testing

**Test against multiple versions:**

```python
@pytest.fixture(scope="session", params=["postgres:15-alpine", "postgres:16-alpine"])
def postgres_container(request):
    """Test against multiple PostgreSQL versions."""
    with PostgresContainer(request.param) as postgres:
        yield postgres
```

**Use when:**
- Supporting multiple database versions
- Verifying upgrade paths
- Ensuring backward compatibility

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

## Complete Working Examples

**Real implementations from production code - copy and adapt these patterns.**

### Example 1: Redis Cache Testing with Lock Auto-Renewal

**Pattern:** Session-scoped Redis + condition-based waiting for async operations

```python
# Fixtures (tests/conftest.py)
@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

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

# Tests (tests/integration/test_internal_cache/test_locks.py)
@pytest.mark.integration
@pytest.mark.asyncio
class TestDistributedLock:
    async def test_lock_auto_renewal(self, redis_client):
        """Test automatic lock renewal using condition-based waiting."""
        from internal_cache import DistributedLock
        from tests.test_utils import wait_for_lock_renewal

        lock = DistributedLock(
            redis_client, "test:auto_renew",
            ttl_seconds=2, auto_renew=True, renew_interval=0.5
        )

        await lock.acquire()
        initial_ttl = await redis_client.ttl("lock:test:auto_renew")

        # Wait for renewal (NO SLEEP - condition-based!)
        await wait_for_lock_renewal(
            redis_client, "lock:test:auto_renew", initial_ttl, timeout_ms=3000
        )

        current_ttl = await redis_client.ttl("lock:test:auto_renew")
        assert current_ttl > initial_ttl - 1
        await lock.release()
```

**Key patterns:**
- ✅ Session-scoped container (fast)
- ✅ Function-scoped client with cleanup
- ✅ Condition-based waiting (no race conditions)
- ✅ Real Redis operations (no mocks)

### Example 2: LocalStack Multi-Service AWS Testing

**Pattern:** One LocalStack container → Multiple AWS services

```python
# Fixtures (tests/integration/test_internal_aws/conftest.py)
@pytest.fixture(scope="session")
def localstack_container():
    localstack = LocalStackContainer(image="localstack/localstack:latest")
    localstack.with_services("s3", "dynamodb", "sqs")
    localstack.start()
    wait_for_logs(localstack, "Ready", timeout=60)
    yield localstack
    localstack.stop()

@pytest.fixture
def sqs_config(localstack_container):
    import boto3
    sqs = boto3.client(
        "sqs", endpoint_url=localstack_container.get_url(),
        region_name="us-east-1", aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    response = sqs.create_queue(QueueName="test-queue")
    return SQSConfig(
        queue_url=response["QueueUrl"], region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )

# Tests (tests/integration/test_internal_aws/test_sqs.py)
@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestSQSClient:
    async def test_send_pydantic_model(self, sqs_client):
        """Test sending Pydantic model to real SQS."""
        class MessageModel(BaseModel):
            id: str
            content: str

        msg = MessageModel(id="123", content="Test")
        response = await sqs_client.send_message(msg)
        assert "MessageId" in response

        messages = await sqs_client.receive_message()
        assert len(messages) >= 1
        body = json.loads(messages[0]["Body"])
        assert body["id"] == "123"
        assert body["content"] == "Test"
```

**Key patterns:**
- ✅ One container, three AWS services
- ✅ Queue creation in config fixture
- ✅ Real SQS operations
- ✅ Pydantic model serialization

### Example 3: MockServer HTTP Client Testing

**Pattern:** Session-scoped MockServer + controlled responses

```python
# Fixtures (tests/integration/test_internal_http/conftest.py)
@pytest.fixture(scope="session")
def mockserver_container():
    """Start MockServer container for HTTP testing."""
    import requests, time
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()

    # Wait for MockServer to be ready
    host = container.get_container_host_ip()
    port = container.get_exposed_port(1080)
    url = f"http://{host}:{port}"

    for _ in range(30):
        try:
            response = requests.put(f"{url}/status", timeout=1.0)
            break  # Any response means server is up
        except (requests.ConnectionError, requests.Timeout):
            time.sleep(1)
    else:
        container.stop()
        raise RuntimeError("MockServer failed to start")

    yield container
    container.stop()

@pytest.fixture(scope="session")
def mock_server_url(mockserver_container):
    """Get MockServer URL."""
    host = mockserver_container.get_container_host_ip()
    port = mockserver_container.get_exposed_port(1080)
    return f"http://{host}:{port}"

@pytest.fixture
def mockserver_client(mock_server_url):
    """Create MockServer client for setting up expectations."""
    from mockserver import MockServerClient
    client = MockServerClient(mock_server_url)
    yield client
    try:
        client.reset()
    except Exception:
        pass

# Tests (tests/integration/test_internal_http/test_http_client_integration.py)
@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientBasicOperations:
    async def test_get_request(self, mock_server_url, mockserver_client):
        """Test GET request with controlled response."""
        from mockserver import request as mock_request, response as mock_response, times

        # Setup expectation
        mockserver_client.stub(
            mock_request(method="GET", path="/get"),
            mock_response(code=200, body={"method": "GET"}),
            times(1)
        )

        async with HttpClient(base_url=mock_server_url) as client:
            response = await client.get("/get")
            assert response.status_code == 200
            assert response.json()["method"] == "GET"

    async def test_retry_on_500(self, mock_server_url, mockserver_client):
        """Test retry behavior with server errors."""
        from mockserver import request as mock_request, response as mock_response, times

        retry_config = RetryConfig(max_retries=3, backoff_factor=0.1)

        # Setup to return 500 multiple times
        mockserver_client.stub(
            mock_request(method="GET", path="/error"),
            mock_response(code=500),
            times(4)  # Will be retried 3 times
        )

        client = HttpClient(base_url=mock_server_url, retries=retry_config)

        with pytest.raises(HttpClientError) as exc_info:
            await client.get("/error")

        assert exc_info.value.status_code == 500
        await client.close()
```

**Key patterns:**
- ✅ Session scope (shared across all tests)
- ✅ Readiness waiting with condition checks
- ✅ Controlled responses via MockServer expectations
- ✅ Test real HTTP client behavior (retries, errors, etc.)
- ✅ Reset expectations between tests

### Example 4: PostgreSQL with Custom Models

**Pattern:** Session container + test-specific schema

```python
# Root fixtures (tests/conftest.py)
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture
def postgres_config(postgres_container):
    return DatabaseConfig(
        driver="postgresql+asyncpg",
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        user=postgres_container.username,
        password=postgres_container.password,
        name=postgres_container.dbname,
    )

# Test-specific fixtures (tests/integration/test_internal_rdbms/test_databases.py)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]

@pytest_asyncio.fixture
async def db_session(postgres_config):
    manager = DatabaseSessionManager(postgres_config)

    # Create schema
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager() as session:
        yield session

    # Cleanup: drop schema
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await manager.close()

# Tests
@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseOperations:
    async def test_create_and_query_user(self, db_session):
        """Test CRUD against real PostgreSQL."""
        user = User(name="Alice", email="alice@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        from sqlalchemy import select
        result = await db_session.execute(
            select(User).where(User.email == "alice@example.com")
        )
        found_user = result.scalar_one()
        assert found_user.name == "Alice"
```

**Key patterns:**
- ✅ Session container (shared)
- ✅ Per-test schema creation/cleanup
- ✅ Real PostgreSQL operations
- ✅ Clean state per test

### Example 5: API-Level End-to-End Testing

**Pattern:** Test entire API endpoint with FastAPI TestClient + real infrastructure

```python
# Fixtures (tests/integration/test_api/conftest.py)
@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture
def app(postgres_config, redis_config):
    """Create FastAPI app with real infrastructure."""
    from myapp import create_app

    app = create_app(
        database_config=postgres_config,
        redis_config=redis_config
    )
    return app

@pytest.fixture
def client(app):
    """TestClient for API testing."""
    from fastapi.testclient import TestClient
    return TestClient(app)

# Tests - End-to-End API workflow
@pytest.mark.integration
@pytest.mark.asyncio
class TestUserAPI:
    def test_create_user_complete_workflow(self, client, db_session):
        """
        Test complete user creation workflow:
        API → Business Logic → PostgreSQL → Response

        This is END-TO-END testing - validates entire service works.
        """
        # Call API endpoint
        response = client.post(
            "/api/users",
            json={"name": "Alice", "email": "alice@example.com"}
        )

        # Verify API response
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Alice"
        assert data["email"] == "alice@example.com"
        user_id = data["id"]

        # Verify data actually persisted to PostgreSQL
        from sqlalchemy import select
        result = db_session.execute(
            select(User).where(User.id == user_id)
        )
        db_user = result.scalar_one()
        assert db_user.name == "Alice"
        assert db_user.email == "alice@example.com"

    def test_get_user_with_cache(self, client, redis_client):
        """
        Test API endpoint with Redis caching:
        API → Check Cache → Database → Update Cache → Response
        """
        # Create user
        create_response = client.post(
            "/api/users",
            json={"name": "Bob", "email": "bob@example.com"}
        )
        user_id = create_response.json()["id"]

        # First GET - hits database, caches in Redis
        response = client.get(f"/api/users/{user_id}")
        assert response.status_code == 200

        # Verify cached in Redis
        cache_key = f"user:{user_id}"
        cached = redis_client.get(cache_key)
        assert cached is not None

        # Second GET - hits cache (verify by checking response time or logs)
        response2 = client.get(f"/api/users/{user_id}")
        assert response2.status_code == 200
        assert response2.json() == response.json()
```

**Key patterns:**
- ✅ Tests complete API workflow end-to-end
- ✅ Multiple infrastructure components (PostgreSQL + Redis)
- ✅ Validates data persistence, caching, response
- ✅ **This is what testcontainers are for** - ensuring your API works with real infrastructure

### Patterns Summary

**All examples demonstrate:**

1. **End-to-End Testing**: Test complete workflows from API/entry point through business logic to infrastructure and back
2. **Three-Fixture Pattern**: Container (session) → Config (function) → Client (function + cleanup)
3. **No Mocking Infrastructure**: Every test uses real databases, caches, queues - catches bugs mocks miss
4. **Condition-Based Waiting**: Readiness checks, async validation, zero race conditions
5. **Proper Cleanup**: `flushdb()`, `drop_all()`, automatic in teardown
6. **Session Reuse**: Containers start once, tests run fast
7. **Production Confidence**: Tests validate actual service behavior, ensuring code won't break in production

## Production Code Examples

The `examples/` directory contains **real, working code** from the python-commons repository (336 tests, 82.95% coverage, 0 flaky tests).

### Available Files

**Configuration Examples (conftest.py):**
- `root_conftest.py` - Multi-container session-scoped fixtures (PostgreSQL, Redis, LocalStack)
- `postgres_conftest.py` - PostgreSQL three-fixture pattern with cleanup
- `mockserver_conftest.py` - MockServer with readiness waiting
- `localstack_conftest.py` - AWS services (S3, DynamoDB, SQS) from single container

**Complete Test Examples:**
- `test_http_client_mockserver.py` - 363 lines of HTTP testing (GET, POST, auth, retry, timeout)
- `test_redis_locks.py` - 436 lines of distributed lock testing with condition-based waiting

**Utilities:**
- `wait_for_condition.py` - Production condition-based waiting utility (eliminates race conditions)

**Documentation:**
- `README.md` - Overview of all examples and usage patterns

### How to Use

1. **Copy entire conftest files** - Drop into your test directories
2. **Adapt patterns** - Modify for your specific services and models
3. **Use utilities as-is** - `wait_for_condition.py` works for any async waiting
4. **Study test examples** - See real-world patterns for testing strategies

All examples are **copy-paste ready** and production-tested.
