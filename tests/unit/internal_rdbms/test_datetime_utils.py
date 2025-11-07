"""Tests for datetime utilities."""

import pytest
from datetime import datetime, timezone, timedelta
from internal_rdbms.utils import ensure_utc


class MockModel:
    """Mock model for testing property decorator."""

    def __init__(self, value: datetime):
        self._value = value

    @ensure_utc
    def value(self) -> datetime:
        return self._value

    @value.setter
    def value(self, val: datetime) -> None:
        self._value = val


@pytest.mark.unit
def test_ensure_utc_with_none():
    """Test ensure_utc handles None values."""
    model = MockModel(None)
    assert model.value is None


@pytest.mark.unit
def test_ensure_utc_with_naive_datetime():
    """Test ensure_utc converts naive datetime to UTC."""
    naive_dt = datetime(2024, 1, 1, 12, 0, 0)
    model = MockModel(naive_dt)

    result = model.value

    assert result.tzinfo is not None
    assert result.tzinfo == timezone.utc
    assert result.year == 2024
    assert result.month == 1
    assert result.day == 1
    assert result.hour == 12
    assert result.minute == 0


@pytest.mark.unit
def test_ensure_utc_with_utc_aware_datetime():
    """Test ensure_utc keeps UTC-aware datetime as-is."""
    utc_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    model = MockModel(utc_dt)

    result = model.value

    assert result.tzinfo == timezone.utc
    assert result == utc_dt


@pytest.mark.unit
def test_ensure_utc_with_non_utc_aware_datetime():
    """Test ensure_utc converts non-UTC aware datetime to UTC."""
    # Create a datetime in EST (UTC-5)
    est = timezone(timedelta(hours=-5))
    est_dt = datetime(2024, 1, 1, 12, 0, 0, tzinfo=est)
    model = MockModel(est_dt)

    result = model.value

    # Should be converted to UTC (17:00)
    assert result.tzinfo == timezone.utc
    assert result.hour == 17  # 12 + 5 = 17 UTC


@pytest.mark.unit
def test_ensure_utc_preserves_property_behavior():
    """Test that ensure_utc decorator preserves property behavior."""
    dt = datetime(2024, 1, 1, 12, 0, 0)
    model = MockModel(dt)

    # Test getter
    value1 = model.value
    assert value1 is not None

    # Test setter
    new_dt = datetime(2024, 12, 31, 23, 59, 59)
    model.value = new_dt
    value2 = model.value

    # Values should be different
    assert value1 != value2
    assert value2.year == 2024
    assert value2.month == 12
    assert value2.day == 31


@pytest.mark.unit
def test_ensure_utc_with_different_timezones():
    """Test ensure_utc with various timezones."""
    # Test with JST (UTC+9)
    jst = timezone(timedelta(hours=9))
    jst_dt = datetime(2024, 1, 1, 21, 0, 0, tzinfo=jst)
    model = MockModel(jst_dt)

    result = model.value

    # Should be converted to UTC (12:00)
    assert result.tzinfo == timezone.utc
    assert result.hour == 12  # 21 - 9 = 12 UTC


@pytest.mark.unit
def test_ensure_utc_multiple_accesses():
    """Test that ensure_utc works correctly on multiple accesses."""
    dt = datetime(2024, 1, 1, 12, 0, 0)
    model = MockModel(dt)

    # Access multiple times
    value1 = model.value
    value2 = model.value
    value3 = model.value

    # All should be equal and UTC-aware
    assert value1 == value2 == value3
    assert value1.tzinfo == timezone.utc
