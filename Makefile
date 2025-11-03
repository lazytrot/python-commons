.PHONY: help install test test-unit test-integration lint format typecheck coverage clean

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install:  ## Install all packages in editable mode with dev dependencies
	pip install -e src/internal_base
	pip install -e src/internal_aws
	pip install -e src/internal_fastapi
	pip install -e src/internal_rdbms
	pip install -e src/internal_cache
	pip install -e ".[dev]"

test:  ## Run all tests with coverage (90% minimum)
	pytest -vv --cov=src --cov-branch --cov-report=term-missing --cov-fail-under=90

test-unit:  ## Run unit tests only (fast, SQLite in-memory)
	pytest -vv -m unit --cov=src --cov-report=term-missing

test-integration:  ## Run integration tests (requires Docker for testcontainers)
	pytest -vv -m integration --cov=src --cov-report=term-missing

test-watch:  ## Run tests in watch mode
	pytest-watch

lint:  ## Run ruff linter
	ruff check src tests

format:  ## Format code with ruff
	ruff format src tests
	ruff check --fix src tests

typecheck:  ## Run mypy type checking
	mypy src

coverage:  ## Generate HTML coverage report
	pytest --cov=src --cov-branch --cov-report=html --cov-report=term
	@echo "Coverage report generated in htmlcov/index.html"

clean:  ## Clean up build artifacts and caches
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf src/**/*.egg-info
	rm -rf .pytest_cache
	rm -rf .ruff_cache
	rm -rf .mypy_cache
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name '*.pyc' -delete

tox:  ## Run tox for all environments
	tox

tox-parallel:  ## Run tox environments in parallel
	tox -p auto

ci:  ## Run CI pipeline (lint, typecheck, test with coverage)
	@echo "==> Running linter..."
	$(MAKE) lint
	@echo "==> Running type checker..."
	$(MAKE) typecheck
	@echo "==> Running tests with coverage..."
	$(MAKE) test
	@echo "==> CI pipeline complete!"

docker-build:  ## Build Docker image for testing
	docker build -t python-commons:test .

docker-test:  ## Run tests inside Docker container
	docker run --rm python-commons:test make test
