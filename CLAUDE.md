# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository is a monorepo containing several independently installable Python packages. The packages are located in the `src/` directory, and each has its own `pyproject.toml` file.

The packages are:
- `internal_base`: Core utilities and foundational code.
- `internal_aws`: Utilities for interacting with Amazon Web Services.
- `internal_fastapi`: Common helpers and configurations for FastAPI-based services.
- `internal_rdbms`: Components for working with relational database management systems.
- `internal_cache`: Redis caching and distributed locking utilities.

## Development Setup

To work on this project, you should first set up a virtual environment:

```bash
python3 -m venv .venv
```

Then, activate the virtual environment:

```bash
source .venv/bin/activate
```

Then, you should install the packages you need in "editable" mode. This allows you to make changes to the source code and have them reflected immediately without reinstalling.

For example, to work on `internal_aws`, you would run the following command from the repository root:

```bash
pip install -e src/internal_aws
```

This will also install its dependencies, like `internal_base`.

If you need to work on multiple packages, you can install them all with a single command:

```bash
pip install -e src/internal_base -e src/internal_aws -e src/internal_fastapi -e src/internal_rdbms -e src/internal_cache
```

## Testing Principles

**We are building the most resilient Python commons library.**

### Core Testing Rules
1. **Avoid mocking as a principle** - Only mock custom things that cannot be reproduced
2. **Use testcontainers to the max** - PostgreSQL, Redis, LocalStack for AWS services
3. **Test against real infrastructure** - No fake implementations
4. **90% code coverage minimum** - All code must be tested
5. **Integration tests over unit tests** - Prefer real service integration
6. **Fast feedback** - SQLite in-memory for fast unit tests, containers for integration

### Test Structure
```
tests/
├── unit/          # Fast tests with SQLite in-memory
├── integration/   # Real services with testcontainers
└── conftest.py    # Shared fixtures (no mocks!)
```

### Running Tests
```bash
# All tests with coverage
tox

# Unit tests only (fast)
tox -e test-unit

# Integration tests only (requires Docker)
tox -e test-integration

# Specific package
pytest tests/unit/internal_rdbms -vv

# With coverage report
pytest --cov=src --cov-report=html
```
