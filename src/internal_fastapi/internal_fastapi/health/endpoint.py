"""
Health check endpoint.

Provides health check functionality for FastAPI applications.
"""

import asyncio
import inspect
from typing import Optional, List, Tuple, Dict, Any, Callable, Union, Awaitable

from fastapi import FastAPI
from pydantic import BaseModel


# Type alias for health check functions
HealthCheckFunc = Callable[[], Union[Awaitable[Dict[str, Any]], Dict[str, Any]]]


def asyncio_is_coroutine_function(func: Callable) -> bool:
    """
    Check if function is a coroutine function.

    Args:
        func: Function to check

    Returns:
        True if coroutine function

    Example:
        async def check():
            return {"status": "ok"}

        asyncio_is_coroutine_function(check)  # True

        def sync_check():
            return {"status": "ok"}

        asyncio_is_coroutine_function(sync_check)  # False
    """
    return asyncio.iscoroutinefunction(func) or inspect.iscoroutinefunction(func)


class HealthResponse(BaseModel):
    """
    Health check response model.

    Example:
        response = HealthResponse(
            status="healthy",
            details={
                "database": {"status": "connected"},
                "cache": {"status": "connected"}
            }
        )
    """

    status: str = "healthy"
    details: Dict[str, Any] = {}


class HealthCheck:
    """
    Health check manager.

    Manages health checks for a FastAPI application with support for
    multiple check functions.

    Example:
        from fastapi import FastAPI
        from internal_fastapi import HealthCheck

        app = FastAPI()
        health = HealthCheck(app, path="/health")

        # Add sync check
        def check_database():
            return {"status": "connected", "connections": 10}

        health.add_check("database", check_database)

        # Add async check
        async def check_cache():
            # Async operation
            return {"status": "connected", "keys": 100}

        health.add_check("cache", check_cache)

        # Health checks are automatically registered
        # GET /health -> {"status": "healthy", "details": {"database": {...}, "cache": {...}}}
    """

    def __init__(self, app: Optional[FastAPI] = None, path: str = "/health"):
        """
        Initialize health check manager.

        Args:
            app: FastAPI application (optional, can add later)
            path: Health check endpoint path

        Example:
            health = HealthCheck(app, path="/health")

            # Or create without app
            health = HealthCheck(path="/healthz")
            # Later: health.add_to_app(app)
        """
        self.path = path
        self.checks: List[Tuple[str, HealthCheckFunc]] = []

        if app:
            self.add_to_app(app)

    def add_check(self, name: str, check_func: HealthCheckFunc) -> None:
        """
        Add a health check function.

        Args:
            name: Check name (e.g., "database", "cache")
            check_func: Check function (sync or async)

        Example:
            # Sync check
            def db_check():
                return {"status": "ok", "latency_ms": 5}

            health.add_check("database", db_check)

            # Async check
            async def redis_check():
                await redis.ping()
                return {"status": "ok"}

            health.add_check("redis", redis_check)
        """
        self.checks.append((name, check_func))

    def add_to_app(self, app: FastAPI, include_in_schema: bool = False) -> None:
        """
        Add health check endpoint to FastAPI app.

        Args:
            app: FastAPI application
            include_in_schema: Include endpoint in OpenAPI schema

        Example:
            app = FastAPI()
            health = HealthCheck()
            health.add_check("db", check_db)
            health.add_to_app(app, include_in_schema=False)
        """
        @app.get(
            self.path,
            response_model=HealthResponse,
            include_in_schema=include_in_schema,
            tags=["health"]
        )
        async def health_check() -> HealthResponse:
            """
            Health check endpoint.

            Returns:
                Health status with check details
            """
            details = {}

            # Run all checks
            for name, check_func in self.checks:
                try:
                    # Call sync or async check
                    if asyncio_is_coroutine_function(check_func):
                        result = await check_func()
                    else:
                        result = check_func()

                    details[name] = result

                except Exception as e:
                    details[name] = {
                        "status": "error",
                        "error": str(e)
                    }

            # Determine overall status
            status = "healthy"
            for check_result in details.values():
                if isinstance(check_result, dict):
                    check_status = check_result.get("status", "").lower()
                    if check_status in ("error", "unhealthy", "down"):
                        status = "unhealthy"
                        break

            return HealthResponse(status=status, details=details)


def create_health_endpoint(
    app: FastAPI,
    path: str = "/health",
    include_in_schema: bool = False,
    checks: Optional[List[Tuple[str, HealthCheckFunc]]] = None
) -> HealthCheck:
    """
    Create and register health check endpoint.

    Factory function for creating health checks with initial checks.

    Args:
        app: FastAPI application
        path: Health check endpoint path
        include_in_schema: Include in OpenAPI schema
        checks: Initial list of (name, check_func) tuples

    Returns:
        HealthCheck instance

    Example:
        from fastapi import FastAPI

        app = FastAPI()

        # Simple health check
        health = create_health_endpoint(app)

        # With custom checks
        def check_db():
            return {"status": "ok"}

        async def check_redis():
            return {"status": "ok"}

        health = create_health_endpoint(
            app,
            path="/healthz",
            checks=[
                ("database", check_db),
                ("redis", check_redis)
            ]
        )

        # Add more checks later
        def check_external_api():
            return {"status": "ok"}

        health.add_check("external_api", check_external_api)
    """
    health = HealthCheck(path=path)

    # Add initial checks
    if checks:
        for name, check_func in checks:
            health.add_check(name, check_func)

    # Register endpoint
    health.add_to_app(app, include_in_schema=include_in_schema)

    return health
