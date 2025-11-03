# Python Commons - Production Readiness Checklist

**Generated**: 2025-11-03
**Target**: Production-ready Python commons library with 90% test coverage
**Policy**: NO MOCKING - Only real services via testcontainers and LocalStack

---

## Overview

This checklist tracks the implementation and validation of all packages in the python-commons monorepo. Each package must be production-ready with comprehensive async support and real integration tests.

---

## Package 1: internal_base

### Core Implementation
- [ ] **Logging Module** (`internal_base/logging_config.py`)
  - [ ] JSON and text logging support
  - [ ] Structured logging with correlation IDs
  - [ ] Log level configuration
  - [ ] Async-safe logging

- [ ] **Settings Module** (`internal_base/secrets.py`, settings)
  - [ ] Install `pydantic-settings>=2.0.0`
  - [ ] Install `pydantic-settings-extra-sources>=0.1.0`
  - [ ] YAML configuration loading
  - [ ] Environment variable substitution
  - [ ] Settings priority: init → env → YAML → .env → defaults
  - [ ] Secrets masking in logs

- [ ] **Health Check Module** (`internal_base/health.py`)
  - [ ] Async health check interface
  - [ ] Component health aggregation
  - [ ] Custom health check registration
  - [ ] Health check response models

- [ ] **Resilience Module** (`internal_base/resilience.py`)
  - [ ] Circuit breaker pattern (pybreaker)
  - [ ] Retry logic with exponential backoff (tenacity)
  - [ ] Timeout handling
  - [ ] Async support for all patterns

- [ ] **Telemetry Module** (`internal_base/telemetry.py`)
  - [ ] OpenTelemetry integration
  - [ ] Trace context propagation
  - [ ] Span creation and management
  - [ ] Metrics collection
  - [ ] Async instrumentation

### Dependencies
- [ ] python-json-logger
- [ ] coloredlogs
- [ ] pydantic>=2.0
- [ ] pydantic-settings>=2.0.0
- [ ] pydantic-settings-extra-sources>=0.1.0
- [ ] opentelemetry-api
- [ ] opentelemetry-sdk
- [ ] opentelemetry-instrumentation
- [ ] tenacity>=8.0.0
- [ ] pybreaker>=1.0.0
- [ ] pyyaml

### Testing
- [ ] **Unit Tests** (SQLite in-memory)
  - [ ] `test_logging.py` - All log formats and levels
  - [ ] `test_health.py` - Health check aggregation
  - [ ] `test_resilience.py` - Circuit breaker, retries, timeouts
  - [ ] `test_secrets.py` - Secret masking
  - [ ] `test_telemetry.py` - Trace and span management
  - [ ] `test_settings.py` - YAML loading and env substitution

- [ ] **Integration Tests** (N/A for base - mostly unit testable)

- [ ] **Coverage**: ≥90%

---

## Package 2: internal_cache

### Core Implementation
- [ ] **Redis Client** (`internal_cache/client.py`)
  - [ ] Async Redis client wrapper (redis.asyncio)
  - [ ] Connection pooling
  - [ ] Automatic reconnection
  - [ ] Key prefix support
  - [ ] TTL management
  - [ ] Pipeline support

- [ ] **Distributed Locks** (`internal_cache/locks.py`)
  - [ ] Async distributed lock implementation
  - [ ] Lock timeout and renewal
  - [ ] Context manager support
  - [ ] Lock release guarantees

- [ ] **Configuration** (`internal_cache/config.py`)
  - [ ] Redis connection settings
  - [ ] Pool configuration
  - [ ] Timeout settings

### Dependencies
- [ ] redis[hiredis]>=5.0.0
- [ ] internal-base (for settings and logging)

### Testing
- [ ] **Unit Tests** (Mock-free, using fakeredis if needed)
  - [ ] `test_config.py` - Configuration validation
  - [ ] `test_locks.py` - Lock logic (with fakeredis)

- [ ] **Integration Tests** (Real Redis via testcontainers)
  - [ ] `test_redis.py` - Full Redis operations
  - [ ] `test_redis_locks.py` - Distributed locks with real Redis
  - [ ] `test_redis_pipeline.py` - Pipeline operations

- [ ] **Coverage**: ≥90%

---

## Package 3: internal_rdbms

### Core Implementation
- [ ] **Base Module** (`internal_rdbms/base.py`)
  - [ ] SQLAlchemy declarative base
  - [ ] Async base model
  - [ ] Timestamp mixins
  - [ ] UUID primary key support

- [ ] **Session Management** (`internal_rdbms/session.py`)
  - [ ] Async session factory
  - [ ] Context manager support
  - [ ] Transaction management
  - [ ] Connection pooling

- [ ] **Repository Pattern** (`internal_rdbms/repository.py`)
  - [ ] Generic async repository base
  - [ ] CRUD operations
  - [ ] Bulk operations
  - [ ] Query builder support

- [ ] **Query Utilities** (`internal_rdbms/query.py`)
  - [ ] Pagination helpers
  - [ ] Filter builders
  - [ ] Sort utilities

- [ ] **Database Drivers**
  - [ ] PostgreSQL (asyncpg)
  - [ ] MySQL (aiomysql)
  - [ ] SQLite (aiosqlite)

### Dependencies
- [ ] sqlalchemy[asyncio]>=2.0.0
- [ ] asyncpg>=0.29.0 (PostgreSQL)
- [ ] aiomysql>=0.2.0 (MySQL)
- [ ] aiosqlite>=0.19.0 (SQLite)
- [ ] alembic>=1.12.0 (migrations)
- [ ] internal-base

### Testing
- [ ] **Unit Tests** (SQLite in-memory)
  - [ ] `test_config.py` - Configuration models
  - [ ] `test_base.py` - Base model functionality
  - [ ] `test_session.py` - Session lifecycle
  - [ ] `test_repository.py` - Repository CRUD operations
  - [ ] `test_query.py` - Query utilities

- [ ] **Integration Tests** (Real databases via testcontainers)
  - [ ] `test_postgres.py` - Full PostgreSQL integration
  - [ ] `test_mysql.py` - Full MySQL integration
  - [ ] `test_transactions.py` - Transaction handling
  - [ ] `test_connection_pool.py` - Pool behavior

- [ ] **Coverage**: ≥90%

---

## Package 4: internal_aws

### Core Implementation
- [ ] **Credentials Module** (`internal_aws/auth/credentials.py`)
  - [ ] Multiple credential providers
  - [ ] Environment credentials
  - [ ] Profile credentials
  - [ ] Explicit credentials
  - [ ] Default credential chain

- [ ] **S3 Client** (`internal_aws/s3/client.py`)
  - [ ] Async S3 operations (aioboto3)
  - [ ] Upload/download files
  - [ ] Stream support
  - [ ] Presigned URLs
  - [ ] Multipart uploads
  - [ ] Object metadata

- [ ] **DynamoDB Client** (`internal_aws/dynamodb/table.py`)
  - [ ] Async DynamoDB operations
  - [ ] Put/Get/Delete items
  - [ ] Query and Scan
  - [ ] Batch operations
  - [ ] Conditional updates
  - [ ] Type serialization

- [ ] **SQS Client** (`internal_aws/sqs/client.py`)
  - [ ] Async SQS operations
  - [ ] Send/receive messages
  - [ ] Batch operations
  - [ ] Message attributes
  - [ ] Visibility timeout

- [ ] **SQS Consumer** (`internal_aws/sqs/consumer.py`)
  - [ ] Long-polling consumer
  - [ ] Concurrent message processing
  - [ ] Error handling
  - [ ] Auto-delete support

### Dependencies
- [ ] aioboto3>=12.0.0
- [ ] boto3>=1.34.0
- [ ] botocore>=1.34.0
- [ ] internal-base

### Testing
- [ ] **Unit Tests** (Configuration and logic)
  - [ ] `test_credentials.py` - Credential providers
  - [ ] `test_s3_config.py` - S3 configuration
  - [ ] `test_dynamodb_config.py` - DynamoDB configuration
  - [ ] `test_sqs_config.py` - SQS configuration

- [ ] **Integration Tests** (Real AWS via LocalStack testcontainer)
  - [ ] `test_s3.py` - S3 operations with LocalStack
  - [ ] `test_dynamodb.py` - DynamoDB operations with LocalStack
  - [ ] `test_sqs.py` - SQS operations with LocalStack
  - [ ] `test_sqs_consumer.py` - Consumer with real SQS

- [ ] **Coverage**: ≥90%

---

## Package 5: internal_fastapi

### Core Implementation
- [ ] **Middleware** (`internal_fastapi/middleware.py`)
  - [ ] Request ID middleware
  - [ ] Logging middleware
  - [ ] Correlation ID propagation
  - [ ] Error handling middleware

- [ ] **Responses** (`internal_fastapi/responses.py`)
  - [ ] Standard response models
  - [ ] Error response models
  - [ ] Pagination response models

- [ ] **Pagination** (`internal_fastapi/pagination.py`)
  - [ ] Cursor-based pagination
  - [ ] Offset-based pagination
  - [ ] Page-based pagination

- [ ] **Dependencies** (`internal_fastapi/dependencies.py`)
  - [ ] Database session dependency
  - [ ] Cache client dependency
  - [ ] Auth dependencies
  - [ ] Settings dependency

- [ ] **Errors** (`internal_fastapi/errors.py`)
  - [ ] Custom exception classes
  - [ ] Exception handlers
  - [ ] Error code mapping

### Dependencies
- [ ] fastapi>=0.109.0
- [ ] uvicorn[standard]>=0.27.0
- [ ] pydantic>=2.0
- [ ] internal-base

### Testing
- [ ] **Unit Tests** (FastAPI test client)
  - [ ] `test_middleware.py` - Middleware behavior
  - [ ] `test_responses.py` - Response models
  - [ ] `test_pagination.py` - Pagination logic
  - [ ] `test_errors.py` - Error handling

- [ ] **Integration Tests** (Real FastAPI with dependencies)
  - [ ] `test_api.py` - Full API with DB and cache
  - [ ] `test_middleware_integration.py` - Middleware with real requests
  - [ ] `test_dependencies.py` - Dependency injection

- [ ] **Coverage**: ≥90%

---

## Package 6: internal_http

### Core Implementation
- [ ] **HTTP Client** (`internal_http/client.py`)
  - [ ] Async HTTP client (httpx)
  - [ ] Retry logic with exponential backoff
  - [ ] Timeout configuration
  - [ ] Connection pooling
  - [ ] Request/response logging

- [ ] **Authentication** (`internal_http/auth.py`)
  - [ ] Bearer token auth
  - [ ] Basic auth
  - [ ] API key auth
  - [ ] Custom auth strategies

- [ ] **Configuration** (`internal_http/config.py`)
  - [ ] Client configuration
  - [ ] Retry configuration
  - [ ] Timeout configuration

### Dependencies
- [ ] httpx>=0.26.0
- [ ] tenacity>=8.0.0 (from internal-base)
- [ ] internal-base

### Testing
- [ ] **Unit Tests** (Logic without real HTTP)
  - [ ] `test_config.py` - Configuration models
  - [ ] `test_auth.py` - Auth strategies

- [ ] **Integration Tests** (Real HTTP via MockServer testcontainer)
  - [ ] `test_client.py` - Full HTTP client with MockServer
  - [ ] `test_retry.py` - Retry logic with real failures
  - [ ] `test_auth_integration.py` - Auth with real requests

- [ ] **Coverage**: ≥90%

---

## Global Testing Infrastructure

### Test Dependencies Setup
- [ ] Update `pyproject.toml` with all test dependencies:
  ```toml
  [project.optional-dependencies]
  dev = [
      # Core testing
      "pytest>=7.4.0",
      "pytest-asyncio>=0.21.0",
      "pytest-cov>=4.1.0",
      "pytest-xdist>=3.3.1",

      # Testcontainers
      "testcontainers>=3.7.1",
      "testcontainers[postgres]>=3.7.1",
      "testcontainers[redis]>=3.7.1",
      "testcontainers[mysql]>=3.7.1",

      # LocalStack for AWS
      "localstack>=3.0.0",

      # Utilities
      "faker>=20.0.0",
      "factory-boy>=3.3.0",
  ]
  ```

### Shared Test Fixtures
- [ ] **`tests/conftest.py`** - Global fixtures
  - [ ] PostgreSQL container fixture (session-scoped)
  - [ ] MySQL container fixture (session-scoped)
  - [ ] Redis container fixture (session-scoped)
  - [ ] LocalStack container fixture (session-scoped)
  - [ ] MockServer container fixture (session-scoped)

### Test Structure
- [ ] Create complete test directory structure
- [ ] Add `__init__.py` to all test directories
- [ ] Configure pytest markers
- [ ] Configure coverage settings

---

## Tox Configuration

- [ ] **`tox.ini`** validation
  - [ ] `test-unit` environment for fast unit tests
  - [ ] `test-integration` environment for integration tests
  - [ ] `test-all` environment for complete test suite
  - [ ] `lint` environment for code quality
  - [ ] `type` environment for type checking

---

## Continuous Integration

- [ ] **GitHub Actions** (`.github/workflows/`)
  - [ ] Unit test workflow (fast, no Docker)
  - [ ] Integration test workflow (with Docker)
  - [ ] Coverage report upload
  - [ ] Linting and formatting checks
  - [ ] Type checking

---

## Documentation

- [ ] **README.md** - Complete with:
  - [ ] Installation instructions
  - [ ] Usage examples for each package
  - [ ] Testing instructions
  - [ ] Contributing guidelines

- [ ] **ARCHITECTURE.md** - ✅ Updated with:
  - [x] pydantic-settings-extra-sources details
  - [x] Testing infrastructure
  - [x] Testcontainers setup

- [ ] **Package-level README** for each package
  - [ ] internal_base/README.md
  - [ ] internal_cache/README.md
  - [ ] internal_rdbms/README.md
  - [ ] internal_aws/README.md
  - [ ] internal_fastapi/README.md
  - [ ] internal_http/README.md

---

## Final Validation

- [ ] **All packages installed in editable mode**
  ```bash
  pip install -e src/internal_base \
              -e src/internal_cache \
              -e src/internal_rdbms \
              -e src/internal_aws \
              -e src/internal_fastapi \
              -e src/internal_http
  ```

- [ ] **All unit tests passing**
  ```bash
  pytest tests/unit -vv --no-cov
  ```

- [ ] **All integration tests passing**
  ```bash
  pytest tests/integration -vv --no-cov
  ```

- [ ] **Coverage ≥90%**
  ```bash
  pytest --cov=src --cov-report=term-missing
  ```

- [ ] **No linting errors**
  ```bash
  ruff check src tests
  ```

- [ ] **Type checking passes**
  ```bash
  mypy src
  ```

- [ ] **All tox environments pass**
  ```bash
  tox
  ```

---

## Package-Specific Detailed Checklists

### internal_base Detailed Tasks
1. [ ] Review existing `logging_config.py` - validate async safety
2. [ ] Review existing `health.py` - ensure proper protocol
3. [ ] Review existing `resilience.py` - validate circuit breaker and retry logic
4. [ ] Review existing `secrets.py` - ensure proper secret masking
5. [ ] Review existing `telemetry.py` - validate OpenTelemetry integration
6. [ ] Create/update settings module with pydantic-settings-extra-sources
7. [ ] Write comprehensive unit tests for each module
8. [ ] Achieve 90%+ coverage

### internal_cache Detailed Tasks
1. [ ] Review existing cache implementation
2. [ ] Ensure async Redis client with connection pooling
3. [ ] Validate distributed lock implementation
4. [ ] Write unit tests with fakeredis (if applicable)
5. [ ] Write integration tests with real Redis (testcontainers)
6. [ ] Test lock timeout and renewal scenarios
7. [ ] Test connection recovery
8. [ ] Achieve 90%+ coverage

### internal_rdbms Detailed Tasks
1. [ ] Review existing base.py, session.py, repository.py
2. [ ] Ensure all operations are async
3. [ ] Validate transaction management
4. [ ] Test with SQLite in-memory for unit tests
5. [ ] Test with real PostgreSQL (testcontainers)
6. [ ] Test with real MySQL (testcontainers)
7. [ ] Test connection pooling behavior
8. [ ] Test transaction rollback scenarios
9. [ ] Achieve 90%+ coverage

### internal_aws Detailed Tasks
1. [ ] Review existing AWS clients
2. [ ] Ensure all operations use aioboto3 (async)
3. [ ] Validate credential provider chain
4. [ ] Create LocalStack fixture for integration tests
5. [ ] Test S3 operations (upload, download, presigned URLs)
6. [ ] Test DynamoDB operations (CRUD, query, scan)
7. [ ] Test SQS operations (send, receive, batch)
8. [ ] Test SQS consumer with message processing
9. [ ] Achieve 90%+ coverage

### internal_fastapi Detailed Tasks
1. [ ] Review existing FastAPI utilities
2. [ ] Ensure middleware is async-safe
3. [ ] Validate pagination implementations
4. [ ] Test error handling and custom exceptions
5. [ ] Create integration tests with real FastAPI app
6. [ ] Test with database and cache dependencies
7. [ ] Test middleware with real requests
8. [ ] Achieve 90%+ coverage

### internal_http Detailed Tasks
1. [ ] **CREATE FROM SCRATCH** - No existing implementation
2. [ ] Implement async HTTP client with httpx
3. [ ] Implement retry logic with exponential backoff
4. [ ] Implement authentication strategies
5. [ ] Implement connection pooling
6. [ ] Write unit tests for configuration and logic
7. [ ] Create MockServer fixture for integration tests
8. [ ] Test retry behavior with simulated failures
9. [ ] Test authentication with real HTTP requests
10. [ ] Achieve 90%+ coverage

---

## Execution Order

**Phase 1: Foundation** (Day 1-2)
1. internal_base - Fix and test completely
2. Update root pyproject.toml with all dependencies
3. Setup global test fixtures in tests/conftest.py

**Phase 2: Data Layer** (Day 2-3)
4. internal_cache - Fix and test
5. internal_rdbms - Fix and test

**Phase 3: Cloud Services** (Day 3-4)
6. internal_aws - Fix and test with LocalStack

**Phase 4: Web Layer** (Day 4-5)
7. internal_http - **Create from scratch** and test
8. internal_fastapi - Fix and test

**Phase 5: Final Validation** (Day 5)
9. Run complete test suite
10. Validate 90% coverage
11. Fix any remaining issues
12. Final documentation pass

---

## Success Criteria

✅ All packages installed without errors
✅ All unit tests pass (< 5 minutes runtime)
✅ All integration tests pass (< 10 minutes runtime)
✅ Overall coverage ≥90%
✅ No linting errors
✅ Type checking passes
✅ All tox environments pass
✅ Documentation complete
✅ **NO MOCKS** - Only real services used

---

**Status**: Ready for execution
**Next Action**: Start with internal_base package audit and fixes
