# Python Commons Test Suite

Comprehensive test suite following **ZERO MOCKING POLICY** - all tests use real services via testcontainers.

## Philosophy

**NO MOCKING** - We test against real infrastructure:
- PostgreSQL via testcontainers
- MySQL via testcontainers
- Redis via testcontainers
- AWS services via LocalStack
- HTTP APIs via MockServer
- SQLite in-memory for fast unit tests

This ensures our code works with actual services, not mocked interfaces.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures
├── pytest.ini               # Pytest configuration
├── requirements-test.txt    # Test dependencies
├── unit/                    # Fast unit tests (SQLite in-memory)
│   ├── internal_base/
│   │   ├── test_logging.py
│   │   └── test_service.py
│   ├── internal_http/
│   ├── internal_rdbms/
│   ├── internal_aws/
│   └── internal_fastapi/
└── integration/             # Integration tests (testcontainers)
    ├── internal_rdbms/
    │   ├── conftest.py      # PostgreSQL, MySQL fixtures
    │   └── test_databases.py
    ├── internal_http/
    │   ├── conftest.py      # MockServer fixtures
    │   └── test_http_client.py
    ├── internal_aws/
    │   ├── conftest.py      # LocalStack fixtures
    │   ├── test_s3.py
    │   ├── test_dynamodb.py
    │   └── test_sqs.py
    └── internal_fastapi/
        └── test_app.py
```

## Requirements

### Docker Required
All integration tests require Docker to run testcontainers:

```bash
# Install Docker
# Ubuntu/Debian
sudo apt-get install docker.io

# macOS
brew install --cask docker

# Verify Docker is running
docker ps
```

### Python Dependencies

```bash
# Install all test dependencies
pip install -r requirements-test.txt

# Or install specific packages
pip install -e src/internal_base[dev]
pip install -e src/internal_http[dev]
pip install -e src/internal_rdbms[dev]
pip install -e src/internal_aws[dev]
pip install -e src/internal_fastapi[dev]
```

## Running Tests

### All Tests
```bash
# Run everything (requires Docker)
pytest

# With verbose output
pytest -v

# With coverage report
pytest --cov=src --cov-report=html
```

### Unit Tests Only (Fast)
```bash
# Unit tests only (no Docker required, uses SQLite in-memory)
pytest -m unit

# Specific package
pytest tests/unit/internal_base/ -v
```

### Integration Tests (Requires Docker)
```bash
# All integration tests
pytest -m integration

# Specific service
pytest -m postgres      # PostgreSQL tests
pytest -m mysql         # MySQL tests
pytest -m redis         # Redis tests
pytest -m localstack    # AWS tests
pytest -m mockserver    # HTTP tests
```

### Package-Specific Tests
```bash
# Test specific package
pytest tests/unit/internal_base/
pytest tests/integration/internal_rdbms/
pytest tests/integration/internal_aws/

# Test specific file
pytest tests/unit/internal_base/test_logging.py -v

# Test specific test
pytest tests/unit/internal_base/test_logging.py::TestLogFormat::test_log_format_values -v
```

### Parallel Execution
```bash
# Install pytest-xdist
pip install pytest-xdist

# Run tests in parallel (4 workers)
pytest -n 4

# Auto-detect number of CPUs
pytest -n auto
```

## Test Coverage

### Generate Coverage Report
```bash
# HTML report (opens in browser)
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Terminal report
pytest --cov=src --cov-report=term-missing

# XML report (for CI)
pytest --cov=src --cov-report=xml
```

### Coverage Goals
- **Target**: 100% code coverage
- **Minimum**: 90% for production code
- All branches covered
- No mocking - real service testing only

## Test Markers

Tests are organized with pytest markers:

```python
@pytest.mark.unit          # Fast unit test (SQLite in-memory)
@pytest.mark.integration   # Integration test (requires Docker)
@pytest.mark.postgres      # Requires PostgreSQL container
@pytest.mark.mysql         # Requires MySQL container
@pytest.mark.redis         # Requires Redis container
@pytest.mark.localstack    # Requires LocalStack (AWS)
@pytest.mark.mockserver    # Requires MockServer (HTTP)
@pytest.mark.slow          # Slow test
@pytest.mark.asyncio       # Async test
```

### Run Specific Markers
```bash
pytest -m "unit"                    # Only unit tests
pytest -m "integration"             # Only integration tests
pytest -m "postgres and not slow"   # PostgreSQL tests, exclude slow
pytest -m "localstack"              # Only AWS tests
```

## Testcontainer Services

### PostgreSQL
```python
@pytest.fixture(scope="session")
def postgres_container():
    """PostgreSQL 15 Alpine container."""
    with PostgresContainer("postgres:15-alpine") as postgres:
        yield postgres
```

### MySQL
```python
@pytest.fixture(scope="session")
def mysql_container():
    """MySQL 8.0 container."""
    with MySqlContainer("mysql:8.0") as mysql:
        yield mysql
```

### Redis
```python
@pytest.fixture(scope="session")
def redis_container():
    """Redis 7 Alpine container."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis
```

### LocalStack (AWS)
```python
@pytest.fixture(scope="session")
def localstack_container():
    """LocalStack for S3, DynamoDB, SQS."""
    with LocalStackContainer() as localstack:
        localstack.with_services("s3", "dynamodb", "sqs")
        yield localstack
```

### MockServer (HTTP)
```python
@pytest.fixture(scope="session")
def mockserver_container():
    """MockServer for HTTP API testing."""
    container = DockerContainer("mockserver/mockserver:latest")
    container.with_exposed_ports(1080)
    container.start()
    yield container
    container.stop()
```

## CI/CD Integration

### GitHub Actions Example
```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      docker:
        image: docker:dind
    
    steps:
      - uses: actions/checkout@v3
      
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
          pip install -e src/internal_base
          pip install -e src/internal_http
          pip install -e src/internal_rdbms
          pip install -e src/internal_aws
          pip install -e src/internal_fastapi
      
      - name: Run tests
        run: pytest --cov=src --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

## Troubleshooting

### Docker Issues
```bash
# Check Docker is running
docker ps

# Pull container images manually
docker pull postgres:15-alpine
docker pull mysql:8.0
docker pull redis:7-alpine
docker pull localstack/localstack:latest
docker pull mockserver/mockserver:latest

# Clean up containers
docker system prune -a
```

### Test Failures
```bash
# Run with verbose output
pytest -vv --tb=long

# Run specific failing test
pytest tests/path/to/test.py::TestClass::test_method -vv

# Show print statements
pytest -s

# Stop on first failure
pytest -x
```

### Coverage Issues
```bash
# Show missing lines
pytest --cov=src --cov-report=term-missing

# Exclude files from coverage
# Edit pytest.ini [coverage:run] omit section
```

## Best Practices

1. **NO MOCKING** - Always use real services via testcontainers
2. **Fast unit tests** - Use SQLite in-memory for speed
3. **Integration tests** - Use testcontainers for real databases
4. **Async tests** - Use `@pytest.mark.asyncio` for async functions
5. **Fixtures** - Reuse fixtures for setup/teardown
6. **Markers** - Tag tests appropriately for selective running
7. **Coverage** - Aim for 100% code coverage
8. **CI/CD** - Run tests in CI pipeline before merge

## Writing New Tests

### Unit Test Example
```python
import pytest
from internal_base import LoggingConfig

@pytest.mark.unit
def test_logging_config():
    """Test logging configuration."""
    config = LoggingConfig(level="DEBUG")
    assert config.level == "DEBUG"
```

### Integration Test Example
```python
import pytest
from internal_rdbms import PostgresDatabase

@pytest.mark.integration
@pytest.mark.postgres
@pytest.mark.asyncio
async def test_postgres_connection(postgres_db):
    """Test PostgreSQL connection with real database."""
    async with postgres_db.session() as session:
        result = await session.execute("SELECT 1")
        assert result is not None
```

## Resources

- [pytest documentation](https://docs.pytest.org/)
- [testcontainers-python documentation](https://testcontainers-python.readthedocs.io/)
- [pytest-asyncio documentation](https://pytest-asyncio.readthedocs.io/)
- [pytest-cov documentation](https://pytest-cov.readthedocs.io/)
