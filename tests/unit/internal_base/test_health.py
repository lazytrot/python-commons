"""Tests for health check utilities."""

import pytest
from internal_base import (
    HealthStatus,
    HealthCheckResult,
    HealthReport,
    HealthChecker,
    check_always_healthy,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_check_always_healthy():
    """Test the always healthy check function."""
    result = await check_always_healthy()

    assert result.status == HealthStatus.HEALTHY
    assert result.message == "Service is alive"
    assert result.name == "liveness"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_all_healthy():
    """Test health checker with all checks passing."""
    checker = HealthChecker()
    checker.register_check("always", check_always_healthy)

    report = await checker.check()

    assert report.status == HealthStatus.HEALTHY
    assert len(report.checks) == 1
    assert report.checks[0].name == "liveness"
    assert report.checks[0].status == HealthStatus.HEALTHY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_with_failure():
    """Test health checker with a failing check."""
    async def failing_check() -> HealthCheckResult:
        return HealthCheckResult(
            name="failing",
            status=HealthStatus.UNHEALTHY,
            message="Service unavailable"
        )

    checker = HealthChecker()
    checker.register_check("failing", failing_check)
    checker.register_check("healthy", check_always_healthy)

    report = await checker.check()

    assert report.status == HealthStatus.UNHEALTHY
    assert len(report.checks) == 2

    # Find checks by name
    failing = next(c for c in report.checks if c.name == "failing")
    healthy = next(c for c in report.checks if c.name == "liveness")

    assert failing.status == HealthStatus.UNHEALTHY
    assert healthy.status == HealthStatus.HEALTHY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_with_degraded():
    """Test health checker with a degraded check."""
    async def degraded_check() -> HealthCheckResult:
        return HealthCheckResult(
            name="degraded",
            status=HealthStatus.DEGRADED,
            message="Running slow"
        )

    checker = HealthChecker()
    checker.register_check("degraded", degraded_check)

    report = await checker.check()

    assert report.status == HealthStatus.DEGRADED
    assert len(report.checks) == 1
    assert report.checks[0].status == HealthStatus.DEGRADED


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_check_exception():
    """Test health checker handles exceptions in checks."""
    async def exception_check() -> HealthCheckResult:
        raise RuntimeError("Something went wrong")

    checker = HealthChecker()
    checker.register_check("exception", exception_check)

    report = await checker.check()

    assert report.status == HealthStatus.UNHEALTHY
    assert len(report.checks) == 1
    assert "Something went wrong" in str(report.checks[0].message)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_mixed_statuses():
    """Test health checker with mixed statuses picks worst."""
    async def healthy_check() -> HealthCheckResult:
        return HealthCheckResult(name="healthy", status=HealthStatus.HEALTHY, message="OK")

    async def degraded_check() -> HealthCheckResult:
        return HealthCheckResult(name="degraded", status=HealthStatus.DEGRADED, message="Slow")

    async def unhealthy_check() -> HealthCheckResult:
        return HealthCheckResult(name="unhealthy", status=HealthStatus.UNHEALTHY, message="Down")

    checker = HealthChecker()
    checker.register_check("healthy", healthy_check)
    checker.register_check("degraded", degraded_check)
    checker.register_check("unhealthy", unhealthy_check)

    report = await checker.check()

    # Should pick worst status (UNHEALTHY)
    assert report.status == HealthStatus.UNHEALTHY
    assert len(report.checks) == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_report_serialization():
    """Test health report can be serialized."""
    checker = HealthChecker()
    checker.register_check("test", check_always_healthy)

    report = await checker.check()

    # Should be able to convert to dict (for JSON responses)
    report_dict = report.to_dict()
    assert "status" in report_dict
    assert "checks" in report_dict
    assert "timestamp" in report_dict
    assert report_dict["status"] == "healthy"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_empty():
    """Test health checker with no checks."""
    checker = HealthChecker()
    report = await checker.check()

    assert report.status == HealthStatus.HEALTHY
    assert len(report.checks) == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_timeout():
    """Test health checker respects timeout."""
    async def slow_check() -> HealthCheckResult:
        import asyncio
        await asyncio.sleep(10)  # Very slow
        return HealthCheckResult(name="slow", status=HealthStatus.HEALTHY)

    checker = HealthChecker()
    checker.register_check("slow", slow_check)

    report = await checker.check(timeout=0.1)

    assert report.status == HealthStatus.UNHEALTHY
    # Should have timeout result
    timeout_check = next((c for c in report.checks if "timeout" in c.name.lower() or "timeout" in c.message.lower()), None)
    assert timeout_check is not None


@pytest.mark.unit
def test_health_check_result_to_dict():
    """Test HealthCheckResult serialization."""
    result = HealthCheckResult(
        name="test-check",
        status=HealthStatus.HEALTHY,
        message="All good",
        details={"version": "1.0", "count": 42}
    )

    result_dict = result.to_dict()

    assert result_dict["name"] == "test-check"
    assert result_dict["status"] == "healthy"
    assert result_dict["message"] == "All good"
    assert result_dict["details"]["version"] == "1.0"
    assert result_dict["details"]["count"] == 42
    assert "timestamp" in result_dict


@pytest.mark.unit
def test_health_report_is_healthy():
    """Test HealthReport is_healthy property."""
    healthy_report = HealthReport(
        status=HealthStatus.HEALTHY,
        checks=[]
    )
    assert healthy_report.is_healthy is True

    unhealthy_report = HealthReport(
        status=HealthStatus.UNHEALTHY,
        checks=[]
    )
    assert unhealthy_report.is_healthy is False

    degraded_report = HealthReport(
        status=HealthStatus.DEGRADED,
        checks=[]
    )
    assert degraded_report.is_healthy is False


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_database_check_success():
    """Test create_database_check with successful connection."""
    from internal_base import create_database_check

    # Create a simple mock DB engine with async execute method
    class MockDBEngine:
        async def execute(self, query):
            return True

    db_engine = MockDBEngine()
    check_func = create_database_check(db_engine)

    result = await check_func()

    assert result.name == "database"
    assert result.status == HealthStatus.HEALTHY
    assert "OK" in result.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_database_check_failure():
    """Test create_database_check with connection failure."""
    from internal_base import create_database_check

    # Create a mock DB engine that fails
    class MockDBEngine:
        async def execute(self, query):
            raise Exception("Connection refused")

    db_engine = MockDBEngine()
    check_func = create_database_check(db_engine)

    result = await check_func()

    assert result.name == "database"
    assert result.status == HealthStatus.UNHEALTHY
    assert "Connection refused" in result.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_database_check_custom_query():
    """Test create_database_check with custom query."""
    from internal_base import create_database_check

    executed_queries = []

    class MockDBEngine:
        async def execute(self, query):
            executed_queries.append(query)
            return True

    db_engine = MockDBEngine()
    check_func = create_database_check(db_engine, query="SELECT NOW()")

    result = await check_func()

    assert result.status == HealthStatus.HEALTHY
    assert "SELECT NOW()" in executed_queries


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_redis_check_success():
    """Test create_redis_check with successful connection."""
    from internal_base import create_redis_check

    # Create a simple mock Redis client with async ping method
    class MockRedisClient:
        async def ping(self):
            return True

    redis_client = MockRedisClient()
    check_func = create_redis_check(redis_client)

    result = await check_func()

    assert result.name == "redis"
    assert result.status == HealthStatus.HEALTHY
    assert "OK" in result.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_create_redis_check_failure():
    """Test create_redis_check with connection failure."""
    from internal_base import create_redis_check

    # Create a mock Redis client that fails
    class MockRedisClient:
        async def ping(self):
            raise Exception("Connection timeout")

    redis_client = MockRedisClient()
    check_func = create_redis_check(redis_client)

    result = await check_func()

    assert result.name == "redis"
    assert result.status == HealthStatus.UNHEALTHY
    assert "Connection timeout" in result.message


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_check_result_with_empty_details():
    """Test HealthCheckResult with empty details dict."""
    result = HealthCheckResult(
        name="test",
        status=HealthStatus.HEALTHY,
        message=None,  # Test None message
        details={}  # Empty details
    )

    result_dict = result.to_dict()

    assert result_dict["name"] == "test"
    assert result_dict["message"] is None
    assert result_dict["details"] == {}


@pytest.mark.unit
def test_determine_overall_status_empty():
    """Test _determine_overall_status with empty results list."""
    checker = HealthChecker()

    # Test with empty list
    status = checker._determine_overall_status([])
    assert status == HealthStatus.HEALTHY


@pytest.mark.unit
@pytest.mark.asyncio
async def test_health_checker_with_non_result_exception():
    """Test health checker handles checks that return unexpected types."""
    async def bad_check():
        # This returns something that's not a HealthCheckResult
        return "not a health check result"

    checker = HealthChecker()
    checker.register_check("bad", bad_check)

    report = await checker.check()

    # Should still work, but might skip the bad result
    assert report.status in [HealthStatus.HEALTHY, HealthStatus.UNHEALTHY]
