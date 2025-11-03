"""Tests for OpenTelemetry instrumentation utilities."""

import pytest
from opentelemetry import trace, metrics
from internal_base import (
    TelemetryConfig,
    setup_telemetry,
    get_tracer,
    get_meter,
    trace_span,
    add_span_attributes,
    add_span_event,
)


@pytest.mark.unit
def test_telemetry_config_creation():
    """Test TelemetryConfig initialization."""
    config = TelemetryConfig(
        service_name="test-service",
        service_version="1.0.0",
        environment="testing",
        enable_console_export=True,
    )

    assert config.service_name == "test-service"
    assert config.service_version == "1.0.0"
    assert config.environment == "testing"
    assert config.enable_console_export is True


@pytest.mark.unit
def test_telemetry_config_defaults():
    """Test TelemetryConfig with default values."""
    config = TelemetryConfig(service_name="test-service")

    assert config.service_name == "test-service"
    assert config.service_version == "0.1.0"
    assert config.environment == "development"
    assert config.enable_console_export is False


@pytest.mark.unit
def test_setup_telemetry():
    """Test telemetry setup."""
    config = TelemetryConfig(
        service_name="test-telemetry",
        service_version="2.0.0",
        environment="production",
        enable_console_export=False,
    )

    # Should not raise any exception
    setup_telemetry(config)

    # Verify tracer provider is set
    tracer = trace.get_tracer(__name__)
    assert tracer is not None


@pytest.mark.unit
def test_setup_telemetry_with_console_export():
    """Test telemetry setup with console export enabled."""
    config = TelemetryConfig(
        service_name="test-console",
        enable_console_export=True,
    )

    # Should not raise any exception
    setup_telemetry(config)

    tracer = trace.get_tracer(__name__)
    assert tracer is not None


@pytest.mark.unit
def test_get_tracer():
    """Test getting a tracer instance."""
    setup_telemetry(TelemetryConfig(service_name="test"))

    tracer = get_tracer("test.module")
    assert tracer is not None


@pytest.mark.unit
def test_get_meter():
    """Test getting a meter instance."""
    setup_telemetry(TelemetryConfig(service_name="test"))

    meter = get_meter("test.module")
    assert meter is not None


@pytest.mark.unit
def test_trace_span_success():
    """Test trace_span context manager with successful execution."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    executed = False
    with trace_span(tracer, "test_operation", {"key": "value"}):
        executed = True

    assert executed is True


@pytest.mark.unit
def test_trace_span_with_exception():
    """Test trace_span context manager with exception."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    with pytest.raises(ValueError, match="test error"):
        with trace_span(tracer, "failing_operation"):
            raise ValueError("test error")


@pytest.mark.unit
def test_trace_span_without_exception_recording():
    """Test trace_span with exception recording disabled."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    with pytest.raises(RuntimeError):
        with trace_span(tracer, "operation", record_exception=False):
            raise RuntimeError("error without recording")


@pytest.mark.unit
def test_add_span_attributes():
    """Test adding attributes to current span."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    with trace_span(tracer, "test_span"):
        # Should not raise even if attributes are added
        add_span_attributes(user_id="123", action="test")


@pytest.mark.unit
def test_add_span_attributes_no_active_span():
    """Test adding attributes when no span is active."""
    setup_telemetry(TelemetryConfig(service_name="test"))

    # Should not raise even without active span
    add_span_attributes(key="value")


@pytest.mark.unit
def test_add_span_event():
    """Test adding event to current span."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    with trace_span(tracer, "test_span"):
        # Should not raise
        add_span_event("cache_hit", {"key": "test_key"})


@pytest.mark.unit
def test_add_span_event_no_active_span():
    """Test adding event when no span is active."""
    setup_telemetry(TelemetryConfig(service_name="test"))

    # Should not raise even without active span
    add_span_event("event_name")


@pytest.mark.unit
def test_add_span_event_with_attributes():
    """Test adding event with attributes."""
    setup_telemetry(TelemetryConfig(service_name="test"))
    tracer = get_tracer(__name__)

    with trace_span(tracer, "test_span"):
        add_span_event("database_query", {"table": "users", "duration_ms": 42})
