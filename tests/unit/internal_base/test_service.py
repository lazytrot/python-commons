"""
Tests for internal_base service module.

Tests ServiceState, BackgroundServiceProtocol, and AsyncService.
"""

import pytest
import asyncio
from internal_base import ServiceState, BackgroundServiceProtocol, AsyncService


class TestServiceState:
    """Test ServiceState enum."""

    def test_service_state_values(self):
        """Test ServiceState enum values."""
        assert ServiceState.IDLE == "idle"
        assert ServiceState.STARTING == "starting"
        assert ServiceState.RUNNING == "running"
        assert ServiceState.STOPPING == "stopping"
        assert ServiceState.STOPPED == "stopped"
        assert ServiceState.FAILED == "failed"

    def test_service_state_str(self):
        """Test ServiceState string representation."""
        assert str(ServiceState.RUNNING) == "running"
        assert str(ServiceState.STOPPED) == "stopped"


class ConcreteService(AsyncService):
    """Concrete service implementation for testing."""

    def __init__(self, name=None, fail_start=False, fail_stop=False, fail_health=False):
        super().__init__(name)
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self.fail_health = fail_health
        self.started = False
        self.stopped = False

    async def _start(self) -> None:
        """Start implementation."""
        if self.fail_start:
            raise RuntimeError("Start failed")
        self.started = True
        await asyncio.sleep(0.01)  # Simulate startup

    async def _stop(self) -> None:
        """Stop implementation."""
        if self.fail_stop:
            raise RuntimeError("Stop failed")
        self.stopped = True
        await asyncio.sleep(0.01)  # Simulate shutdown

    async def _health_check(self) -> bool:
        """Health check implementation."""
        if self.fail_health:
            return False
        return self.started and not self.stopped


@pytest.mark.asyncio
class TestAsyncService:
    """Test AsyncService abstract base class."""

    async def test_initial_state(self):
        """Test service starts in IDLE state."""
        service = ConcreteService()
        assert service.state == ServiceState.IDLE

    async def test_start_service(self):
        """Test starting a service."""
        service = ConcreteService()
        await service.start()
        
        assert service.state == ServiceState.RUNNING
        assert service.started is True

    async def test_stop_service(self):
        """Test stopping a service."""
        service = ConcreteService()
        await service.start()
        await service.stop()
        
        assert service.state == ServiceState.STOPPED
        assert service.stopped is True

    async def test_start_twice(self):
        """Test starting service twice is idempotent."""
        service = ConcreteService()
        await service.start()
        await service.start()  # Should not raise
        
        assert service.state == ServiceState.RUNNING

    async def test_stop_without_start(self):
        """Test stopping service without starting."""
        service = ConcreteService()
        await service.stop()
        
        # Should handle gracefully
        assert service.state in (ServiceState.IDLE, ServiceState.STOPPED)

    async def test_health_check_running(self):
        """Test health check on running service."""
        service = ConcreteService()
        await service.start()
        
        is_healthy = await service.is_healthy()
        assert is_healthy is True

    async def test_health_check_stopped(self):
        """Test health check on stopped service."""
        service = ConcreteService()
        await service.start()
        await service.stop()
        
        is_healthy = await service.is_healthy()
        assert is_healthy is False

    async def test_health_check_failed(self):
        """Test health check when check fails."""
        service = ConcreteService(fail_health=True)
        await service.start()
        
        is_healthy = await service.is_healthy()
        assert is_healthy is False

    async def test_context_manager(self):
        """Test using service as async context manager."""
        service = ConcreteService()
        
        async with service:
            assert service.state == ServiceState.RUNNING
            assert service.started is True
        
        assert service.state == ServiceState.STOPPED
        assert service.stopped is True

    async def test_start_failure(self):
        """Test handling start failure."""
        service = ConcreteService(fail_start=True)
        
        with pytest.raises(RuntimeError, match="Start failed"):
            await service.start()
        
        assert service.state == ServiceState.FAILED

    async def test_service_name(self):
        """Test service name."""
        service1 = ConcreteService()
        assert service1._name == "ConcreteService"
        
        service2 = ConcreteService(name="CustomName")
        assert service2._name == "CustomName"
