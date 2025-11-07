# Real Production Examples

This directory contains **real, working code** from the python-commons repository (336 tests, 82.95% coverage, 0 flaky tests).

## Files

### Configuration Examples (conftest.py)

- **root_conftest.py** - Root-level session-scoped container fixtures
  - PostgreSQL container (shared across 50+ tests)
  - Redis container (shared across 30+ tests)
  - LocalStack container (shared across 40+ tests)
  - Shows multi-container orchestration

- **postgres_conftest.py** - PostgreSQL-specific fixtures
  - Database config extraction from container
  - Session management with cleanup
  - Three-fixture pattern: Container → Config → Session

- **mockserver_conftest.py** - MockServer for HTTP testing
  - Container readiness waiting
  - MockServer client setup with reset
  - Shows condition-based waiting for container startup

- **localstack_conftest.py** - LocalStack AWS services
  - S3, DynamoDB, SQS configuration
  - AWS credentials setup
  - Multi-service from single container

### Test Examples

- **test_http_client_mockserver.py** - Complete HTTP client tests
  - GET, POST, PUT, PATCH, DELETE operations
  - Headers, auth (Bearer, Basic)
  - Retry logic, timeout handling
  - MockServer expectations with stub()
  - 364 lines of production-tested HTTP testing

- **test_redis_locks.py** - Redis distributed locks
  - Lock acquisition and renewal
  - Condition-based waiting for lock expiry
  - Real Redis integration (no mocking)
  - Shows async patterns with pytest-asyncio

### Utilities

- **wait_for_condition.py** - Condition-based waiting utility
  - Eliminates race conditions in tests
  - Async/sync condition support
  - Clear timeout messages
  - Production-tested pattern that fixed 11 flaky tests

## Key Patterns Demonstrated

1. **Session-Scoped Container Reuse** - Start containers once, share across tests
2. **Three-Fixture Pattern** - Container → Config → Client for optimal isolation
3. **Condition-Based Waiting** - Wait for actual conditions, not arbitrary sleeps
4. **Multi-Container Orchestration** - Share PostgreSQL + Redis + LocalStack
5. **Cleanup Strategies** - Service-specific cleanup (flushdb, drop tables, etc.)
6. **MockServer Expectations** - HTTP testing with controlled responses
7. **Async Patterns** - pytest-asyncio for async clients

## Usage

These are **copy-paste ready** examples. You can:
1. Copy entire conftest.py files to your test directories
2. Adapt the patterns to your specific services
3. Use wait_for_condition.py as-is for reliable waiting
4. Study test examples for testing strategies

## Metrics

These patterns power:
- 336 tests in ~45 seconds
- 0 flaky tests (condition-based waiting)
- 0 mocking (all real services)
- 82.95% code coverage
- Zero production breaks from missed bugs
