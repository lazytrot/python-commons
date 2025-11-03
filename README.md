# Python Commons

A collection of production-ready Python utilities for cloud-deployed microservices.

## 📦 Packages

### `internal_base` - Core Foundation
Essential utilities for all services:
- **Settings**: Pydantic-based configuration with `pydantic-settings-extra-sources` support
- **Telemetry**: OpenTelemetry tracing and metrics
- **Health Checks**: Kubernetes-compatible health/readiness/liveness endpoints
- **Resilience**: Retry logic (Tenacity) and circuit breakers (PyBreaker)
- **Secrets**: Abstract secrets provider with environment/AWS/chained support
- **Logging**: JSON and colored console logging

### `internal_aws` - AWS Integration
AWS service wrappers with async support:
- **S3**: Upload/download, presigned URLs, object operations
- **SQS**: Message queuing with batch operations
- **SNS**: Pub/sub messaging and SMS
- **Secrets Manager**: Secrets provider implementation
- **SSM Parameter Store**: Configuration retrieval
- **Lambda**: Decorators and event parsing
- **CloudWatch**: Metrics and logging

### `internal_fastapi` - API Framework
FastAPI utilities for REST APIs:
- **Middleware**: Request ID, timing, CORS, security headers
- **Error Handling**: Standardized error responses with exception handlers
- **Responses**: Typed response envelopes (success, error, paginated)
- **Pagination**: Offset-based and cursor-based pagination
- **Dependencies**: Auth, DB session injection patterns

### `internal_rdbms` - Database Layer
SQLAlchemy utilities for PostgreSQL/MySQL:
- **Base Models**: Declarative base with mixins (timestamps, soft delete, audit)
- **Session Management**: Async session factory with connection pooling
- **Repository Pattern**: Generic CRUD operations with type safety
- **Query Builder**: Fluent API for dynamic filtering/sorting/pagination

### `internal_cache` - Redis Caching
Redis utilities for caching and coordination:
- **Redis Client**: Async wrapper with JSON serialization
- **Cache Decorators**: `@cached` and `@cache_aside` for function memoization
- **Distributed Locks**: Redlock implementation with auto-renewal

## 🚀 Installation

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install all packages in editable mode
pip install -e src/internal_base -e src/internal_aws -e src/internal_fastapi -e src/internal_rdbms -e src/internal_cache
```

## 🧪 Testing

Use **testcontainers** for integration tests with PostgreSQL and Redis:

```python
import pytest
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:15") as postgres:
        yield postgres
```

See individual package documentation for detailed usage examples.
