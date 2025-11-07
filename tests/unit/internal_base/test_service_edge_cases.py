"""
Additional edge case tests for AsyncService.

Tests uncovered edge cases in async_service.py.
"""

import pytest
from internal_base.service.async_service import AsyncService
from internal_base.service.protocol import ServiceState


class SimpleService(AsyncService):
    """Simple test service."""

    def __init__(self, name=None, fail_start=False, fail_stop=False, fail_health=False):
        super().__init__(name)
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self.fail_health = fail_health
        self.started = False
        self.stopped = False

    async def _start(self) -> None:
        if self.fail_start:
            raise RuntimeError("Start failed")
        self.started = True

    async def _stop(self) -> None:
        if self.fail_stop:
            raise RuntimeError("Stop failed")
        self.stopped = True

    async def _health_check(self) -> bool:
        if self.fail_health:
            raise RuntimeError("Health check failed")
        return True


class TestAsyncServiceEdgeCases:
    """Test AsyncService edge cases."""

    @pytest.mark.asyncio
    async def test_start_in_starting_state(self):
        """Test start when service is in STARTING state."""
        service = SimpleService()
        service._state = ServiceState.STARTING

        with pytest.raises(RuntimeError, match="Cannot start service"):
            await service.start()

    @pytest.mark.asyncio
    async def test_start_in_stopping_state(self):
        """Test start when service is in STOPPING state."""
        service = SimpleService()
        service._state = ServiceState.STOPPING

        with pytest.raises(RuntimeError, match="Cannot start service"):
            await service.start()

    @pytest.mark.asyncio
    async def test_start_in_failed_state(self):
        """Test start when service is in FAILED state."""
        service = SimpleService()
        service._state = ServiceState.FAILED

        with pytest.raises(RuntimeError, match="Cannot start service"):
            await service.start()

    @pytest.mark.asyncio
    async def test_stop_in_starting_state(self):
        """Test stop when service is in STARTING state."""
        service = SimpleService()
        service._state = ServiceState.STARTING

        with pytest.raises(RuntimeError, match="Cannot stop service"):
            await service.stop()

    @pytest.mark.asyncio
    async def test_stop_in_stopping_state(self):
        """Test stop when service is in STOPPING state."""
        service = SimpleService()
        service._state = ServiceState.STOPPING

        with pytest.raises(RuntimeError, match="Cannot stop service"):
            await service.stop()

    @pytest.mark.asyncio
    async def test_stop_in_failed_state(self):
        """Test stop when service is in FAILED state."""
        service = SimpleService()
        service._state = ServiceState.FAILED

        with pytest.raises(RuntimeError, match="Cannot stop service"):
            await service.stop()

    @pytest.mark.asyncio
    async def test_start_failure_sets_failed_state(self):
        """Test that start failure sets FAILED state."""
        service = SimpleService(fail_start=True)

        with pytest.raises(RuntimeError, match="Start failed"):
            await service.start()

        assert service.state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_stop_failure_sets_failed_state(self):
        """Test that stop failure sets FAILED state."""
        service = SimpleService(fail_stop=True)

        # Start service first
        await service.start()
        assert service.state == ServiceState.RUNNING

        # Now stop should fail
        with pytest.raises(RuntimeError, match="Stop failed"):
            await service.stop()

        assert service.state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_health_check_when_not_running(self):
        """Test health check when service is not running."""
        service = SimpleService()

        # Health check should return False when not running
        assert await service.is_healthy() is False

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health check when _health_check raises exception."""
        service = SimpleService(fail_health=True)

        # Start service
        await service.start()
        assert service.state == ServiceState.RUNNING

        # Health check should return False on exception
        assert await service.is_healthy() is False

    @pytest.mark.asyncio
    async def test_context_manager_with_failure(self):
        """Test context manager when service fails during operation."""
        service = SimpleService()

        try:
            async with service as s:
                assert s.state == ServiceState.RUNNING
                # Simulate failure
                raise ValueError("Operation failed")
        except ValueError:
            pass

        # Service should still be stopped
        assert service.state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_start_from_stopped_state(self):
        """Test starting a service that was previously stopped."""
        service = SimpleService()

        # Start and stop
        await service.start()
        await service.stop()
        assert service.state == ServiceState.STOPPED

        # Should be able to start again
        await service.start()
        assert service.state == ServiceState.RUNNING
        assert service.started is True

    @pytest.mark.asyncio
    async def test_default_service_name(self):
        """Test default service name is class name."""
        service = SimpleService()
        assert service.name == "SimpleService"

    @pytest.mark.asyncio
    async def test_custom_service_name(self):
        """Test custom service name."""
        service = SimpleService(name="MyCustomService")
        assert service.name == "MyCustomService"

    @pytest.mark.asyncio
    async def test_state_property(self):
        """Test state property."""
        service = SimpleService()
        assert service.state == ServiceState.IDLE

        await service.start()
        assert service.state == ServiceState.RUNNING

        await service.stop()
        assert service.state == ServiceState.STOPPED
