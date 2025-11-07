"""
Unit tests for service protocol.

Tests BackgroundServiceProtocol and ServiceState.
"""

import pytest
from internal_base.service.protocol import BackgroundServiceProtocol, ServiceState


class TestServiceState:
    """Test ServiceState enum."""

    def test_all_states_exist(self):
        """Test all service state values."""
        assert ServiceState.IDLE.value == "idle"
        assert ServiceState.STARTING.value == "starting"
        assert ServiceState.RUNNING.value == "running"
        assert ServiceState.STOPPING.value == "stopping"
        assert ServiceState.STOPPED.value == "stopped"
        assert ServiceState.FAILED.value == "failed"

    def test_str_representation(self):
        """Test string representation."""
        assert str(ServiceState.IDLE) == "idle"
        assert str(ServiceState.RUNNING) == "running"
        assert str(ServiceState.FAILED) == "failed"


class TestBackgroundServiceProtocol:
    """Test BackgroundServiceProtocol."""

    def test_protocol_is_runtime_checkable(self):
        """Test that protocol is runtime_checkable."""
        class ValidService:
            @property
            def state(self) -> ServiceState:
                return ServiceState.IDLE

            async def start(self) -> None:
                pass

            async def stop(self) -> None:
                pass

            async def is_healthy(self) -> bool:
                return True

        service = ValidService()
        # Should be recognized as implementing the protocol
        assert isinstance(service, BackgroundServiceProtocol)

    def test_protocol_rejects_invalid_implementation(self):
        """Test that protocol rejects incomplete implementations."""
        class InvalidService:
            # Missing required methods
            pass

        service = InvalidService()
        # Should not be recognized as implementing the protocol
        assert not isinstance(service, BackgroundServiceProtocol)

    def test_protocol_with_partial_implementation(self):
        """Test protocol with partial implementation."""
        class PartialService:
            @property
            def state(self) -> ServiceState:
                return ServiceState.IDLE

            async def start(self) -> None:
                pass

            # Missing stop() and is_healthy()

        service = PartialService()
        # Should not fully implement the protocol
        assert not isinstance(service, BackgroundServiceProtocol)
