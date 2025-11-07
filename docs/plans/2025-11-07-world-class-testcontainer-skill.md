# World-Class Testcontainer Testing Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the testcontainer-testing skill into a comprehensive, world-class testing implementation guide that enables engineers to create maximum-impact test suites with zero guesswork.

**Architecture:** Enhance existing skill with real code patterns from python-commons repository, add condition-based waiting patterns, httpbin/HTTP testing, multi-container orchestration, container versioning best practices, and complete working examples from actual implementations.

**Tech Stack:** Python, pytest, testcontainers-python, Docker, pytest-asyncio, httpbin, LocalStack, Redis, PostgreSQL

---

## Task 1: Add Condition-Based Waiting Patterns Section

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md` (after line 153)
- Reference: `/home/lazytrot/work/python-commons/tests/test_utils/wait.py`
- Reference: `/home/lazytrot/work/python-commons/tests/integration/test_internal_aws/test_sqs.py:229-233`

**Step 1: Add new section header after "Cleanup Strategies"**

Insert after line 153 in SKILL.md:

```markdown
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
# httpbin example
async def httpbin_url(httpbin_container):
    """Get httpbin base URL and wait for it to be ready."""
    host = httpbin_container.get_container_host_ip()
    port = httpbin_container.get_exposed_port(80)
    url = f"http://{host}:{port}"

    # Wait for httpbin to be ready
    async with httpx.AsyncClient() as client:
        async def check_ready():
            try:
                response = await client.get(f"{url}/get", timeout=1.0)
                return response.status_code == 200
            except (httpx.ConnectError, httpx.TimeoutException):
                return False

        await wait_for_condition(
            check_ready,
            "httpbin container to be ready",
            timeout_ms=30000  # 30 seconds
        )

    return url
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
```

**Step 2: Verify markdown formatting**

Run: `cat /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md | grep -A 5 "Condition-Based Waiting"`
Expected: Section header visible

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: add condition-based waiting patterns section"
```

---

## Task 2: Add HTTP Testing with httpbin Pattern

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md` (after "Common Services" section)
- Reference: `/home/lazytrot/work/python-commons/tests/integration/test_internal_http/test_http_client_integration.py`
- Reference: `/home/lazytrot/work/python-commons/tests/integration/test_internal_http/conftest.py`

**Step 1: Add httpbin section after Redis section (after line 218)**

Insert after Redis example:

```markdown
### httpbin (HTTP Client Testing)

**Use case:** Test HTTP clients against real HTTP server without mocking.

```python
@pytest.fixture(scope="module")
def httpbin_container():
    """Start httpbin container for HTTP testing."""
    from testcontainers.core.container import DockerContainer

    container = DockerContainer("kennethreitz/httpbin:latest")
    container.with_exposed_ports(80)
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="module")
async def httpbin_url(httpbin_container):
    """Get httpbin base URL and wait for it to be ready."""
    import httpx
    import asyncio

    host = httpbin_container.get_container_host_ip()
    port = httpbin_container.get_exposed_port(80)
    url = f"http://{host}:{port}"

    # Wait for httpbin to be ready (condition-based waiting!)
    async with httpx.AsyncClient() as client:
        for _ in range(30):  # Try for 30 seconds
            try:
                response = await client.get(f"{url}/get", timeout=1.0)
                if response.status_code == 200:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(1)
        else:
            raise RuntimeError("httpbin container failed to start")

    return url
```

**Why httpbin:**
- ✅ Perfect for HTTP client testing
- ✅ Supports all HTTP methods (GET, POST, PUT, DELETE, PATCH)
- ✅ Echo endpoints for validation
- ✅ Auth testing (Basic, Bearer)
- ✅ Status code testing
- ✅ Delay/timeout testing

**Example tests:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientBasicOperations:
    """Test basic HTTP operations."""

    async def test_get_request(self, httpbin_url):
        """Test GET request."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.get("/get")

            assert response.status_code == 200
            data = response.json()
            assert "url" in data

    async def test_post_json(self, httpbin_url):
        """Test POST with JSON body."""
        async with HttpClient(base_url=httpbin_url) as client:
            payload = {"name": "test", "value": 42}
            response = await client.post("/post", json=payload)

            assert response.status_code == 200
            data = response.json()
            assert data["json"] == payload

    async def test_bearer_auth(self, httpbin_url):
        """Test Bearer token authentication."""
        auth_config = AuthConfig(auth=BearerAuth("test-token-123"))
        async with HttpClient(base_url=httpbin_url, auth_config=auth_config) as client:
            response = await client.get("/bearer")

            # httpbin /bearer endpoint requires Bearer token
            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["token"] == "test-token-123"

    async def test_retry_on_500(self, httpbin_url):
        """Test retry on server error."""
        retry_config = RetryConfig(max_retries=3, backoff_factor=0.1)
        client = HttpClient(base_url=httpbin_url, retries=retry_config)

        # httpbin /status/500 returns 500 error
        with pytest.raises(HttpClientError) as exc_info:
            await client.get("/status/500")

        assert exc_info.value.status_code == 500
        await client.close()
```

**httpbin useful endpoints:**
- `/get`, `/post`, `/put`, `/delete`, `/patch` - Echo requests
- `/status/{code}` - Return specific status code
- `/bearer` - Test Bearer auth
- `/basic-auth/{user}/{pass}` - Test Basic auth
- `/delay/{seconds}` - Test timeout handling
- `/headers` - Inspect headers sent
```

**Step 2: Verify section was added**

Run: `grep -n "httpbin" /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md`
Expected: Multiple matches showing httpbin section

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: add httpbin HTTP testing pattern"
```

---

## Task 3: Add Multi-Container Test Suite Guide

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md` (new section before "Anti-Patterns")
- Reference: `/home/lazytrot/work/python-commons/tests/integration/test_internal_aws/conftest.py`
- Reference: `/home/lazytrot/work/python-commons/tests/conftest.py`

**Step 1: Add multi-container section before "Anti-Patterns to Avoid"**

Insert before line 253:

```markdown
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
│   ├── redis_container                # Starts ONCE for ALL tests
│   ├── postgres_config                # Function-scoped (per-test config)
│   └── redis_client                   # Function-scoped (per-test client + cleanup)
│
├── integration/
│   ├── test_internal_aws/
│   │   ├── conftest.py                # AWS-specific fixtures
│   │   │   ├── localstack_container   # SESSION-SCOPED (3 services in 1)
│   │   │   ├── s3_config              # Function-scoped
│   │   │   ├── dynamodb_config        # Function-scoped
│   │   │   ├── sqs_config             # Function-scoped
│   │   │   └── s3_client              # Function-scoped with cleanup
│   │   ├── test_s3.py                 # Uses s3_client
│   │   ├── test_dynamodb.py           # Uses dynamodb fixtures
│   │   └── test_sqs.py                # Uses sqs_client
│   │
│   ├── test_internal_cache/
│   │   ├── test_locks.py              # Uses redis_client from root conftest
│   │   └── test_cache.py              # Uses redis_client from root conftest
│   │
│   └── test_internal_rdbms/
│       └── test_databases.py          # Uses postgres_config from root conftest
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
```

**Step 2: Verify addition**

Run: `grep -n "Multi-Container Test Suites" /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md`
Expected: Line number showing new section

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: add multi-container test suite guide"
```

---

## Task 4: Add Container Versioning Best Practices

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md` (new section after "Performance Tips")

**Step 1: Add versioning section after "Performance Tips"**

Insert after performance section:

```markdown
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
DockerContainer("kennethreitz/httpbin:latest")      # httpbin (stable)
DockerContainer("mockserver/mockserver:5.15.0")     # MockServer 5.15.0
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
```

**Step 2: Verify versioning section**

Run: `grep -A 3 "Container Versioning Best Practices" /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md`
Expected: Section header and first few lines

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: add container versioning best practices"
```

---

## Task 5: Enhance Overview with Real-World Context

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md:6-10`

**Step 1: Replace generic overview with concrete examples**

Replace lines 6-10:

```markdown
# Testcontainer Testing

## Overview

This skill transforms how you write integration tests. Instead of mocking databases, caches, and cloud services, you'll test against real infrastructure using Docker containers - achieving both realistic testing AND fast execution through proven container reuse patterns.

**Real Results:**
- python-commons repository: 336 tests, 82.95% coverage, 0 flaky tests, 0 mocking
- Integration tests run in seconds, not minutes
- Containers shared across entire test suite (PostgreSQL starts once for 50+ tests)
- Zero mock behavior - every test validates real service integration

**This skill provides battle-tested patterns from production codebases.**
```

**Step 2: Verify change**

Run: `head -n 20 /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md | grep "Real Results"`
Expected: Shows new overview text

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: enhance overview with real-world results"
```

---

## Task 6: Add Complete Working Example Section

**Files:**
- Modify: `/home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md` (new section before "Workflow")
- Reference: Complete integration test examples from python-commons

**Step 1: Add complete working example before "Workflow" section**

Insert before line 400:

```markdown
## Complete Working Examples

**Real implementations from production code - copy and adapt these patterns.**

### Example 1: Redis Cache Testing (Complete Suite)

**Fixtures:** `tests/conftest.py`

```python
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
    """Provide Redis client connected to real Redis container."""
    client = RedisClient(redis_config)
    await client.connect()

    yield client

    # Cleanup: flush database
    await client.client.flushdb()
    await client.close()
```

**Tests:** `tests/integration/test_internal_cache/test_locks.py`

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestDistributedLock:
    """Test distributed lock with real Redis - NO MOCKING."""

    async def test_acquire_and_release(self, redis_client):
        """Test lock acquisition and release."""
        from internal_cache import DistributedLock

        lock = DistributedLock(redis_client, "test:resource", ttl_seconds=10)

        # Acquire lock
        acquired = await lock.acquire()
        assert acquired is True

        # Verify lock exists in Redis
        exists = await redis_client.exists("lock:test:resource")
        assert exists == 1

        # Release lock
        await lock.release()

        # Verify lock removed
        exists = await redis_client.exists("lock:test:resource")
        assert exists == 0

    async def test_lock_auto_renewal(self, redis_client):
        """Test automatic lock renewal."""
        from internal_cache import DistributedLock
        from tests.test_utils import wait_for_lock_renewal

        lock = DistributedLock(
            redis_client,
            "test:auto_renew",
            ttl_seconds=2,
            auto_renew=True,
            renew_interval=0.5
        )

        await lock.acquire()

        # Capture initial TTL
        initial_ttl = await redis_client.ttl("lock:test:auto_renew")

        # Wait for renewal (condition-based waiting!)
        await wait_for_lock_renewal(
            redis_client,
            "lock:test:auto_renew",
            initial_ttl,
            timeout_ms=3000
        )

        # Verify lock was renewed
        current_ttl = await redis_client.ttl("lock:test:auto_renew")
        assert current_ttl > initial_ttl - 1

        await lock.release()
```

**Key patterns:**
- ✅ Session-scoped container (fast)
- ✅ Function-scoped client with cleanup (isolated)
- ✅ Condition-based waiting (no flaky tests)
- ✅ Tests against real Redis (no mocking)

### Example 2: LocalStack AWS Testing (Multi-Service)

**Fixtures:** `tests/integration/test_internal_aws/conftest.py`

```python
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
def sqs_config(localstack_container):
    """SQS configuration for LocalStack."""
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
```

**Tests:** `tests/integration/test_internal_aws/test_sqs.py`

```python
@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestSQSClient:
    """Test SQSClient with real LocalStack SQS."""

    async def test_send_and_receive_message(self, sqs_client):
        """Test sending and receiving message."""
        # Send message
        response = await sqs_client.send_message("Hello, SQS!")
        assert "MessageId" in response

        # Receive message
        messages = await sqs_client.receive_message(max_number_of_messages=1)
        assert len(messages) >= 1
        assert messages[0]["Body"] == "Hello, SQS!"

    async def test_send_pydantic_model(self, sqs_client):
        """Test sending Pydantic model."""
        from pydantic import BaseModel

        class MessageModel(BaseModel):
            id: str
            content: str

        msg = MessageModel(id="123", content="Test content")

        response = await sqs_client.send_message(msg)
        assert "MessageId" in response

        # Receive and parse
        messages = await sqs_client.receive_message()
        assert len(messages) >= 1

        import json
        body = json.loads(messages[0]["Body"])
        assert body["id"] == "123"
        assert body["content"] == "Test content"
```

**Key patterns:**
- ✅ One LocalStack container for multiple AWS services
- ✅ Real SQS operations (no mocking)
- ✅ Queue creation in config fixture
- ✅ Tests validate actual AWS API behavior

### Example 3: httpbin HTTP Client Testing

**Fixtures:** `tests/integration/test_internal_http/test_http_client_integration.py`

```python
@pytest.fixture(scope="module")
def httpbin_container():
    """Start httpbin container for HTTP testing."""
    container = DockerContainer("kennethreitz/httpbin:latest")
    container.with_exposed_ports(80)
    container.start()

    yield container

    container.stop()


@pytest.fixture(scope="module")
async def httpbin_url(httpbin_container):
    """Get httpbin base URL and wait for it to be ready."""
    import httpx
    import asyncio

    host = httpbin_container.get_container_host_ip()
    port = httpbin_container.get_exposed_port(80)
    url = f"http://{host}:{port}"

    # Wait for httpbin to be ready (condition-based waiting!)
    async with httpx.AsyncClient() as client:
        for _ in range(30):
            try:
                response = await client.get(f"{url}/get", timeout=1.0)
                if response.status_code == 200:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                await asyncio.sleep(1)
        else:
            raise RuntimeError("httpbin container failed to start")

    return url
```

**Tests:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestHttpClientBasicOperations:
    """Test basic HTTP operations."""

    async def test_get_with_params(self, httpbin_url):
        """Test GET with query parameters."""
        async with HttpClient(base_url=httpbin_url) as client:
            response = await client.get("/get", params={"foo": "bar", "test": "123"})

            data = response.json()
            assert data["args"]["foo"] == "bar"
            assert data["args"]["test"] == "123"

    async def test_bearer_auth(self, httpbin_url):
        """Test Bearer token authentication."""
        auth_config = AuthConfig(auth=BearerAuth("test-token-123"))
        async with HttpClient(base_url=httpbin_url, auth_config=auth_config) as client:
            response = await client.get("/bearer")

            assert response.status_code == 200
            data = response.json()
            assert data["authenticated"] is True
            assert data["token"] == "test-token-123"

    async def test_timeout_error(self, httpbin_url):
        """Test timeout handling."""
        client = HttpClient(base_url=httpbin_url, timeout=0.001)

        # /delay endpoint will timeout
        with pytest.raises(HttpClientError):
            await client.get("/delay/5")

        await client.close()
```

**Key patterns:**
- ✅ Module-scoped container (shared across test class)
- ✅ Readiness waiting before tests run
- ✅ Real HTTP requests (no mocking)
- ✅ Tests actual timeout, auth, retry behavior

### Example 4: PostgreSQL Database Testing

**Fixtures:** `tests/conftest.py` + test-specific setup

```python
# Root conftest.py
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
```

**Test-specific fixtures:**

```python
# tests/integration/test_internal_rdbms/test_databases.py

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Base class for test models."""
    pass


class User(Base):
    """Test user model."""
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    email: Mapped[str]


@pytest_asyncio.fixture
async def db_session(postgres_config):
    """Create database session with schema."""
    from internal_rdbms import DatabaseSessionManager

    manager = DatabaseSessionManager(postgres_config)

    # Create tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with manager() as session:
        yield session

    # Cleanup: drop tables
    async with manager.engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await manager.close()
```

**Tests:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
class TestDatabaseOperations:
    """Test database operations with real PostgreSQL."""

    async def test_create_and_query_user(self, db_session):
        """Test creating and querying user."""
        # Create user
        user = User(name="Alice", email="alice@example.com")
        db_session.add(user)
        await db_session.commit()
        await db_session.refresh(user)

        # Query user
        from sqlalchemy import select
        result = await db_session.execute(
            select(User).where(User.email == "alice@example.com")
        )
        found_user = result.scalar_one()

        assert found_user.name == "Alice"
        assert found_user.email == "alice@example.com"
```

**Key patterns:**
- ✅ Session-scoped container (shared)
- ✅ Function-scoped session with schema creation/cleanup
- ✅ Real PostgreSQL operations
- ✅ Each test gets clean database

### Patterns Summary

**All examples demonstrate:**

1. **Three-Fixture Pattern**
   - Container (session-scoped)
   - Config (function-scoped)
   - Client/Session (function-scoped with cleanup)

2. **No Mocking**
   - Every test uses real service
   - Validates actual behavior

3. **Condition-Based Waiting**
   - Container readiness checks
   - Async operation validation
   - Zero race conditions

4. **Proper Cleanup**
   - `flushdb()` for Redis
   - `drop_all()` for databases
   - Automatic in fixture teardown

5. **Session Reuse**
   - Containers start once
   - Fast test execution
   - Resource efficient
```

**Step 2: Verify examples section**

Run: `grep -n "Complete Working Examples" /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md`
Expected: Line number showing section

**Step 3: Commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: add complete working examples section"
```

---

## Task 7: Refine and Review (Iteration 1)

**Step 1: Read entire SKILL.md for consistency**

Run: `wc -l /home/lazytrot/.claude/skills/testcontainer-testing/SKILL.md`
Expected: ~800-1000 lines (significantly expanded)

**Step 2: Check for duplicate content**

Manually review for:
- Duplicate code examples
- Contradictory advice
- Missing cross-references

**Step 3: Ensure progressive disclosure**

Verify structure flows from:
1. Overview → Quick Start → Core Patterns → Complete Examples → Advanced Topics

**Step 4: Add cross-references**

Update sections to reference each other:
- Quick Start → points to Complete Examples
- Anti-Patterns → points to correct patterns
- Cleanup Strategies → points to Condition-Based Waiting

**Step 5: Commit refinements**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: first refinement pass - consistency and flow"
```

---

## Task 8: Refine and Review (Iteration 2 - Final Polish)

**Step 1: Verify all code examples are syntactically correct**

Check:
- All imports present
- Async/await usage consistent
- Fixture scopes explicitly stated
- No placeholder code

**Step 2: Add missing markers and metadata**

Ensure all test examples include:
```python
@pytest.mark.integration
@pytest.mark.asyncio  # if async
```

**Step 3: Verify container versions are pinned**

Check all examples use:
- `postgres:15-alpine` (not `postgres:latest`)
- `redis:7-alpine` (not `redis:latest`)
- Specific versions documented

**Step 4: Add performance metrics**

Include timing information where relevant:
- "Container starts in ~2s"
- "Test suite: 336 tests in 45s"
- "Session reuse: 20s → 2s"

**Step 5: Final read-through**

Read entire document as if you're an engineer with zero context:
- Is every concept explained?
- Are examples copy-pasteable?
- Is the "why" clear for every pattern?

**Step 6: Final commit**

```bash
cd /home/lazytrot/.claude/skills/testcontainer-testing
git add SKILL.md
git commit -m "docs: final polish - world-class testcontainer skill complete"
```

---

## Success Criteria

☐ Condition-based waiting patterns section added with real code
☐ httpbin HTTP testing pattern documented with examples
☐ Multi-container test suite guide with architecture diagram
☐ Container versioning best practices with recommendations
☐ Enhanced overview with real-world metrics
☐ Complete working examples from 4+ services
☐ All code examples syntactically correct and copy-pasteable
☐ Cross-references between sections
☐ Progressive disclosure (simple → advanced)
☐ Zero contradictions or duplicate content
☐ Every pattern includes "why" explanation
☐ Performance metrics included
☐ Git commits document each enhancement

---

## Post-Implementation

**Test the skill:**

1. Use skill to write new integration tests
2. Verify patterns are clear and actionable
3. Confirm code examples work without modification
4. Validate it creates "maximum impact bang for buck"

**Share and iterate:**

1. The skill is now world-class
2. Future updates should maintain quality bar
3. Add new services as patterns emerge
