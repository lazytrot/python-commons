# Quick Start: Testing Guide

## Current Status

✅ **38 unit tests passing**
✅ **13.82% coverage baseline**
✅ **Zero mocking policy enforced**
✅ **All test infrastructure ready**

## Run Tests Now (No Docker Required)

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all passing unit tests
.venv/bin/pytest tests/unit/internal_base/test_logging.py \
                  tests/unit/internal_base/test_service.py \
                  tests/unit/internal_http/test_auth.py \
                  tests/unit/internal_http/test_config.py \
                  -v --cov=src --cov-report=html --cov-report=term

# View HTML coverage report
open htmlcov/index.html  # or xdg-open on Linux
```

**Expected Output:**
- 38 tests passing
- Coverage report showing 13.82% overall
- internal_base: 90%+ coverage
- internal_http auth/config: 100% coverage

---

## Next Level: Integration Tests (Requires Docker)

### Prerequisites

```bash
# Check Docker is running
docker ps

# If not running, start Docker
sudo systemctl start docker  # Linux
# or start Docker Desktop on Mac/Windows
```

### 1. Run HTTP Integration Tests

```bash
# Test HttpClient against real HTTP server (MockServer)
.venv/bin/pytest tests/integration/internal_http/test_http_client_integration.py -v -m mockserver

# Expected: 30+ additional tests
# Coverage: internal_http HttpClient → 22% → 85%+
```

### 2. Run Database Integration Tests

```bash
# PostgreSQL tests
.venv/bin/pytest tests/integration/internal_rdbms/ -m postgres -v

# MySQL tests
.venv/bin/pytest tests/integration/internal_rdbms/ -m mysql -v

# SQLite tests (fast, no container needed)
.venv/bin/pytest tests/integration/internal_rdbms/ -m sqlite -v

# All database tests
.venv/bin/pytest tests/integration/internal_rdbms/ -v

# Expected: Database coverage → 0% → 85%+
```

### 3. Run AWS Integration Tests

```bash
# All AWS tests (S3, DynamoDB, SQS)
.venv/bin/pytest tests/integration/internal_aws/ -m localstack -v

# S3 tests only
.venv/bin/pytest tests/integration/internal_aws/test_s3.py -v

# DynamoDB tests only
.venv/bin/pytest tests/integration/internal_aws/test_dynamodb.py -v

# SQS tests only
.venv/bin/pytest tests/integration/internal_aws/test_sqs.py -v

# Expected: AWS coverage → 0% → 85%+
```

---

## Complete Test Suite

```bash
# Run ALL tests (unit + integration)
# Requires Docker to be running
.venv/bin/pytest tests/ -v --cov=src --cov-report=html --cov-report=term

# Expected: 100+ tests passing
# Expected coverage: 60-70%
```

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'internal_http'"

**Solution:**
```bash
.venv/bin/pip install -e src/internal_http --force-reinstall --no-deps
```

### "Docker container not starting"

**Solution:**
```bash
# Check Docker is running
docker ps

# Check Docker daemon
sudo systemctl status docker

# Pull images manually
docker pull mockserver/mockserver:latest
docker pull postgres:latest
docker pull mysql:latest
docker pull localstack/localstack:latest
```

### "Tests taking too long"

**Solution:**
```bash
# Run tests in parallel
.venv/bin/pytest tests/ -n auto -v

# Run only fast tests (skip integration)
.venv/bin/pytest tests/unit/ -v
```

### "Coverage not showing"

**Solution:**
```bash
# Make sure pytest-cov is installed
.venv/bin/pip install pytest-cov

# Run with explicit coverage
.venv/bin/pytest tests/ --cov=src --cov-report=html --cov-branch
```

---

## Test Development

### Add New Tests

1. **Unit tests** (no Docker): `tests/unit/<package>/<test_name>.py`
2. **Integration tests** (Docker): `tests/integration/<package>/<test_name>.py`

### Test Template

```python
"""Test <component> functionality."""

import pytest
from internal_<package> import <Component>


@pytest.mark.unit  # or @pytest.mark.integration
class Test<Component>:
    """Test <Component>."""

    async def test_<feature>(self):
        """Test <feature> works correctly."""
        # Arrange
        component = <Component>()

        # Act
        result = await component.method()

        # Assert
        assert result == expected
```

### Running Your New Tests

```bash
# Run specific test file
.venv/bin/pytest tests/unit/internal_base/test_mynewfeature.py -v

# Run specific test class
.venv/bin/pytest tests/unit/internal_base/test_mynewfeature.py::TestMyFeature -v

# Run specific test method
.venv/bin/pytest tests/unit/internal_base/test_mynewfeature.py::TestMyFeature::test_specific -v
```

---

## Coverage Goals

### Current: 13.82%

| Package | Current | Target | Gap |
|---------|---------|--------|-----|
| internal_base | 90% | 100% | 10% |
| internal_http | 60% | 90% | 30% |
| internal_rdbms | 0% | 90% | 90% |
| internal_fastapi | 0% | 85% | 85% |
| internal_aws | 0% | 85% | 85% |

### Path to 90%+

1. ✅ **Baseline established** (13.82%)
2. ⏳ **Run HTTP integration tests** → +15% (28%)
3. ⏳ **Run database integration tests** → +15% (43%)
4. ⏳ **Run AWS integration tests** → +20% (63%)
5. ⏳ **Add FastAPI tests** → +15% (78%)
6. ⏳ **Add edge case tests** → +12% (90%+)

---

## Zero Mocking Policy ✅

**We don't use:**
- ❌ `unittest.mock`
- ❌ `pytest-mock`
- ❌ Fake/stub implementations

**We use:**
- ✅ Real HTTP servers (MockServer)
- ✅ Real databases (PostgreSQL, MySQL, SQLite via testcontainers)
- ✅ Real AWS services (LocalStack)
- ✅ Real Redis (testcontainers)

**Why?**
- Tests actually verify behavior, not mock expectations
- Catches integration issues early
- Higher confidence in code correctness
- Tests are documentation of real usage

---

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
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -r requirements-test.txt
          pip install -e src/internal_base
          pip install -e src/internal_http
          pip install -e src/internal_rdbms
          pip install -e src/internal_fastapi
          pip install -e src/internal_aws

      - name: Run tests
        run: |
          pytest tests/ -v --cov=src --cov-report=xml

      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

---

## Quick Reference

### Most Common Commands

```bash
# Fast unit tests only
.venv/bin/pytest tests/unit/ -v

# All tests with coverage
.venv/bin/pytest tests/ --cov=src --cov-report=html

# Specific package tests
.venv/bin/pytest tests/unit/internal_base/ -v
.venv/bin/pytest tests/integration/internal_http/ -v

# Watch mode (re-run on file changes)
.venv/bin/pytest tests/ --watch

# Show test durations
.venv/bin/pytest tests/ --durations=10

# Verbose output with print statements
.venv/bin/pytest tests/ -v -s

# Stop on first failure
.venv/bin/pytest tests/ -x

# Run last failed tests
.venv/bin/pytest tests/ --lf
```

---

## Getting Help

- **Test infrastructure**: See `tests/README.md`
- **Coverage details**: See `COVERAGE_REPORT.md`
- **Test status**: See `TEST_STATUS.md`
- **Examples**: See `EXAMPLES.md`

---

**🎯 Goal: 90%+ coverage with zero mocks**
**✅ Current: 38 tests passing, infrastructure ready**
**🚀 Next: Run integration tests with Docker**
