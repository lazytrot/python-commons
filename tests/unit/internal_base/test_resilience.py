"""Tests for resilience patterns (retry and circuit breaker)."""

import asyncio
import pytest
from pybreaker import CircuitBreakerError
from internal_base import (
    retry_with_exponential_backoff,
    retry_on_transient_errors,
    ServiceCircuitBreaker,
    resilient_call,
    is_transient_error,
)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_success():
    """Test retry decorator with successful execution."""
    call_count = 0

    @retry_with_exponential_backoff(max_attempts=3)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_eventual_success():
    """Test retry decorator that succeeds after failures."""
    call_count = 0

    @retry_with_exponential_backoff(max_attempts=3, min_wait=0.01, max_wait=0.1)
    async def flaky_function():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ConnectionError("temporary failure")
        return "success"

    result = await flaky_function()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_max_attempts():
    """Test retry decorator exhausts max attempts."""
    call_count = 0

    @retry_with_exponential_backoff(max_attempts=3, min_wait=0.01, max_wait=0.1)
    async def always_fails():
        nonlocal call_count
        call_count += 1
        raise ConnectionError("persistent failure")

    with pytest.raises(ConnectionError, match="persistent failure"):
        await always_fails()

    assert call_count == 3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_with_specific_exceptions():
    """Test retry only on specific exception types."""
    call_count = 0

    @retry_with_exponential_backoff(
        max_attempts=3, min_wait=0.01, exceptions=(ConnectionError,)
    )
    async def specific_exception():
        nonlocal call_count
        call_count += 1
        raise ValueError("not retryable")

    with pytest.raises(ValueError, match="not retryable"):
        await specific_exception()

    # Should fail immediately without retries
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_retry_on_transient_errors():
    """Test retry on common transient errors."""
    call_count = 0

    @retry_on_transient_errors(max_attempts=3)
    async def transient_failures():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise ConnectionError("connection failed")
        elif call_count == 2:
            raise TimeoutError("timeout")
        return "success"

    result = await transient_failures()
    assert result == "success"
    assert call_count == 3


@pytest.mark.unit
def test_service_circuit_breaker_creation():
    """Test ServiceCircuitBreaker initialization."""
    breaker = ServiceCircuitBreaker(
        name="test-service",
        fail_max=5,
        reset_timeout=60.0,
    )

    assert breaker.name == "test-service"
    assert breaker.state == "closed"
    assert breaker.failure_count == 0


@pytest.mark.unit
def test_circuit_breaker_opens_after_failures():
    """Test circuit breaker opens after max failures."""
    breaker = ServiceCircuitBreaker(name="test", fail_max=3, reset_timeout=1.0)

    def failing_function():
        raise RuntimeError("failure")

    # Trigger failures to open circuit
    # First 2 calls raise RuntimeError
    for _ in range(2):
        with pytest.raises(RuntimeError):
            breaker.call(failing_function)

    # 3rd call opens the circuit and raises CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        breaker.call(failing_function)

    # Circuit should be open now
    assert breaker.state == "open"
    assert breaker.failure_count == 3


@pytest.mark.unit
def test_circuit_breaker_rejects_when_open():
    """Test circuit breaker rejects calls when open."""
    breaker = ServiceCircuitBreaker(name="test", fail_max=2, reset_timeout=1.0)

    def failing_function():
        raise RuntimeError("failure")

    # Open the circuit
    # First call raises RuntimeError
    with pytest.raises(RuntimeError):
        breaker.call(failing_function)

    # Second call opens circuit and raises CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        breaker.call(failing_function)

    # Circuit is now open, next call should also raise CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        breaker.call(failing_function)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_async_call():
    """Test circuit breaker with async functions."""
    breaker = ServiceCircuitBreaker(name="async-test", fail_max=3)

    call_count = 0

    async def async_function():
        nonlocal call_count
        call_count += 1
        return "success"

    result = await breaker.call_async(async_function)
    assert result == "success"
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_async_failure():
    """Test circuit breaker with failing async functions."""
    breaker = ServiceCircuitBreaker(name="async-fail", fail_max=2, reset_timeout=1.0)

    async def failing_async():
        raise ConnectionError("async failure")

    # Trigger failures
    # First call raises ConnectionError
    with pytest.raises(ConnectionError):
        await breaker.call_async(failing_async)

    # Second call opens circuit and raises CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        await breaker.call_async(failing_async)

    # Circuit should be open, third call also raises CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        await breaker.call_async(failing_async)


@pytest.mark.unit
def test_circuit_breaker_exclude_exceptions():
    """Test circuit breaker with excluded exceptions."""
    breaker = ServiceCircuitBreaker(
        name="test-exclude",
        fail_max=2,
        exclude_exceptions=(ValueError,),
    )

    def raises_excluded():
        raise ValueError("excluded")

    # These should not count toward failure threshold
    # Excluded exceptions pass through without opening circuit
    for _ in range(5):
        with pytest.raises(ValueError):
            breaker.call(raises_excluded)

    # Circuit should still be closed because ValueError is excluded
    assert breaker.state == "closed"
    assert breaker.failure_count == 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resilient_call_decorator():
    """Test resilient_call combining retry and circuit breaker."""
    breaker = ServiceCircuitBreaker(name="resilient-test", fail_max=5)
    call_count = 0

    @resilient_call(circuit_breaker=breaker, max_retries=3)
    async def flaky_service():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ConnectionError("temporary")
        return "success"

    result = await flaky_service()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resilient_call_without_circuit_breaker():
    """Test resilient_call with only retry logic."""
    call_count = 0

    @resilient_call(max_retries=3, retry_exceptions=(TimeoutError,))
    async def retry_only():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError("timeout")
        return "success"

    result = await retry_only()
    assert result == "success"
    assert call_count == 2


@pytest.mark.unit
def test_is_transient_error():
    """Test transient error detection."""
    assert is_transient_error(ConnectionError("connection lost")) is True
    assert is_transient_error(TimeoutError("timeout")) is True
    assert is_transient_error(OSError("os error")) is True
    assert is_transient_error(ValueError("bad value")) is False
    assert is_transient_error(RuntimeError("runtime error")) is False


@pytest.mark.unit
def test_circuit_breaker_decorator():
    """Test using circuit breaker as decorator."""
    breaker = ServiceCircuitBreaker(name="decorator-test", fail_max=3)

    call_count = 0

    @breaker.decorator
    def decorated_function():
        nonlocal call_count
        call_count += 1
        return "result"

    result = decorated_function()
    assert result == "result"
    assert call_count == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Test circuit breaker transitions to half-open and recovers."""
    breaker = ServiceCircuitBreaker(name="recovery-test", fail_max=2, reset_timeout=0.1)

    attempts = 0

    def failing_then_succeeding():
        nonlocal attempts
        attempts += 1
        if attempts <= 2:
            raise RuntimeError("initial failures")
        return "recovered"

    # Trigger failures to open circuit
    # First call raises RuntimeError
    with pytest.raises(RuntimeError):
        breaker.call(failing_then_succeeding)

    # Second call opens circuit and raises CircuitBreakerError
    with pytest.raises(CircuitBreakerError):
        breaker.call(failing_then_succeeding)

    assert breaker.state == "open"

    # Wait for reset timeout to allow half-open state
    await asyncio.sleep(0.15)

    # Next call should succeed and close the circuit
    result = breaker.call(failing_then_succeeding)
    assert result == "recovered"
    assert breaker.state == "closed"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_circuit_breaker_call_async_non_coroutine():
    """Test call_async with a regular function that returns a coroutine."""
    breaker = ServiceCircuitBreaker(name="test", fail_max=3)

    async def async_operation():
        return "result"

    # Call through call_async with a function that returns a coroutine
    def wrapper():
        return async_operation()

    result = await breaker.call_async(wrapper)
    assert result == "result"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resilient_call_with_circuit_breaker_open():
    """Test resilient_call rejects when circuit breaker is open."""
    breaker = ServiceCircuitBreaker(name="test", fail_max=2)

    # Open the circuit
    for _ in range(2):
        with pytest.raises((RuntimeError, CircuitBreakerError)):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("error")))

    assert breaker.state == "open"

    @resilient_call(circuit_breaker=breaker, max_retries=2)
    async def failing_call():
        return "should not reach"

    # Should immediately reject due to open circuit
    with pytest.raises(CircuitBreakerError):
        await failing_call()


@pytest.mark.unit
def test_resilient_call_sync_with_circuit_breaker():
    """Test resilient_call with sync function and circuit breaker."""
    breaker = ServiceCircuitBreaker(name="sync-test", fail_max=5)
    call_count = 0

    @resilient_call(circuit_breaker=breaker, max_retries=3)
    def sync_function():
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise TimeoutError("temp failure")
        return "success"

    result = sync_function()
    assert result == "success"
    assert call_count == 2
    assert breaker.state == "closed"


@pytest.mark.unit
def test_resilient_call_sync_with_circuit_breaker_open():
    """Test resilient_call with sync function when circuit is open."""
    breaker = ServiceCircuitBreaker(name="sync-open-test", fail_max=2)

    # Open the circuit
    for _ in range(2):
        with pytest.raises((RuntimeError, CircuitBreakerError)):
            breaker.call(lambda: (_ for _ in ()).throw(RuntimeError("error")))

    assert breaker.state == "open"

    @resilient_call(circuit_breaker=breaker, max_retries=2)
    def sync_call():
        return "should not reach"

    # Should immediately reject due to open circuit
    with pytest.raises(CircuitBreakerError):
        sync_call()


@pytest.mark.unit
def test_circuit_breaker_state_change_to_closed(caplog):
    """Test circuit breaker state change callback when transitioning to closed."""
    import logging
    caplog.set_level(logging.INFO)

    breaker = ServiceCircuitBreaker(name="state-test", fail_max=2, reset_timeout=0.1)

    # Manually trigger state change to closed (tests line 155-156)
    # Create mock state objects
    class MockState:
        def __init__(self, name):
            self.name = name

    old_state = MockState("half-open")
    new_state = MockState("closed")

    breaker.state_change(breaker._breaker, old_state, new_state)

    # Verify logging occurred
    assert "closed" in caplog.text


@pytest.mark.unit
def test_circuit_breaker_state_change_to_half_open(caplog):
    """Test circuit breaker state change callback when transitioning to half-open."""
    import logging
    caplog.set_level(logging.INFO)

    breaker = ServiceCircuitBreaker(name="half-open-test", fail_max=2)

    # Create mock state objects
    class MockState:
        def __init__(self, name):
            self.name = name

    old_state = MockState("open")
    new_state = MockState("half-open")

    breaker.state_change(breaker._breaker, old_state, new_state)

    # Verify logging occurred
    assert "half-open" in caplog.text
