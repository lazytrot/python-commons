"""
Unit tests for lifecycle manager.

Tests LifecycleManager for FastAPI service coordination.
"""

import pytest
import asyncio
import signal
from fastapi import FastAPI
from internal_fastapi.api.lifecycle_manager import LifecycleManager, ServiceState, BackgroundServiceProtocol


class MockService:
    """Mock service for testing."""

    def __init__(self, name="MockService", fail_start=False, fail_stop=False):
        self.name = name
        self.fail_start = fail_start
        self.fail_stop = fail_stop
        self._state = ServiceState.IDLE
        self.started = False
        self.stopped = False

    @property
    def state(self) -> ServiceState:
        return self._state

    async def start(self) -> None:
        if self.fail_start:
            self._state = ServiceState.FAILED
            raise RuntimeError(f"Failed to start {self.name}")
        self._state = ServiceState.RUNNING
        self.started = True

    async def stop(self) -> None:
        if self.fail_stop:
            raise RuntimeError(f"Failed to stop {self.name}")
        self._state = ServiceState.STOPPED
        self.stopped = True

    async def is_healthy(self) -> bool:
        return self._state == ServiceState.RUNNING

    def __str__(self):
        return self.name


class TestLifecycleManager:
    """Test LifecycleManager."""

    def test_init(self):
        """Test manager initialization."""
        manager = LifecycleManager()
        assert manager._services == []
        assert manager._setup_handler is None
        assert manager._state == ServiceState.IDLE

    def test_add_service(self):
        """Test adding a service."""
        manager = LifecycleManager()
        service = MockService("Service1")

        manager.add_service(service)

        assert len(manager._services) == 1
        assert manager._services[0] == service

    def test_add_multiple_services(self):
        """Test adding multiple services."""
        manager = LifecycleManager()
        service1 = MockService("Service1")
        service2 = MockService("Service2")

        manager.add_service(service1)
        manager.add_service(service2)

        assert len(manager._services) == 2
        assert manager._services[0] == service1
        assert manager._services[1] == service2

    def test_set_setup_handler(self):
        """Test setting setup handler."""
        manager = LifecycleManager()

        async def my_setup():
            return [MockService("Setup1")]

        manager.set_setup_handler(my_setup)
        assert manager._setup_handler == my_setup

    @pytest.mark.asyncio
    async def test_start_services(self):
        """Test starting services."""
        manager = LifecycleManager()
        service1 = MockService("Service1")
        service2 = MockService("Service2")

        manager.add_service(service1)
        manager.add_service(service2)

        await manager.start()

        assert service1.started is True
        assert service2.started is True
        assert manager._state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_start_with_setup_handler(self):
        """Test starting with setup handler."""
        manager = LifecycleManager()

        async def setup():
            return [MockService("Dynamic1"), MockService("Dynamic2")]

        manager.set_setup_handler(setup)

        # Add one service manually
        manual_service = MockService("Manual")
        manager.add_service(manual_service)

        await manager.start()

        # Should have 3 services total (1 manual + 2 from setup)
        assert len(manager._services) == 3
        assert manual_service.started is True
        assert all(s.started for s in manager._services)

    @pytest.mark.asyncio
    async def test_start_already_running(self):
        """Test starting when already running."""
        manager = LifecycleManager()
        service = MockService()
        manager.add_service(service)

        await manager.start()
        assert manager._state == ServiceState.RUNNING

        # Try to start again
        await manager.start()

        # Should still be running, no error
        assert manager._state == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_start_failure(self):
        """Test start failure handling."""
        manager = LifecycleManager()
        service = MockService(fail_start=True)
        manager.add_service(service)

        with pytest.raises(RuntimeError, match="Failed to start"):
            await manager.start()

        assert manager._state == ServiceState.FAILED

    @pytest.mark.asyncio
    async def test_stop_services(self):
        """Test stopping services."""
        manager = LifecycleManager()
        service1 = MockService("Service1")
        service2 = MockService("Service2")

        manager.add_service(service1)
        manager.add_service(service2)

        await manager.start()
        await manager.stop()

        assert service1.stopped is True
        assert service2.stopped is True
        assert manager._state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_reverse_order(self):
        """Test services are stopped in reverse order."""
        manager = LifecycleManager()
        stop_order = []

        class OrderedService(MockService):
            async def stop(self):
                stop_order.append(self.name)
                await super().stop()

        service1 = OrderedService("First")
        service2 = OrderedService("Second")
        service3 = OrderedService("Third")

        manager.add_service(service1)
        manager.add_service(service2)
        manager.add_service(service3)

        await manager.start()
        await manager.stop()

        # Should stop in reverse order
        assert stop_order == ["Third", "Second", "First"]

    @pytest.mark.asyncio
    async def test_stop_already_stopped(self):
        """Test stopping when already stopped."""
        manager = LifecycleManager()
        service = MockService()
        manager.add_service(service)

        await manager.start()
        await manager.stop()

        assert manager._state == ServiceState.STOPPED

        # Try to stop again
        await manager.stop()

        # Should still be stopped, no error
        assert manager._state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_stop_with_error(self):
        """Test stop continues even if a service fails to stop."""
        manager = LifecycleManager()
        service1 = MockService("Service1")
        service2 = MockService("Service2", fail_stop=True)
        service3 = MockService("Service3")

        manager.add_service(service1)
        manager.add_service(service2)
        manager.add_service(service3)

        await manager.start()
        await manager.stop()

        # Services 1 and 3 should still stop even if 2 fails
        assert service1.stopped is True
        assert service3.stopped is True
        assert manager._state == ServiceState.STOPPED

    def test_status_property(self):
        """Test status property."""
        manager = LifecycleManager()
        assert manager.status == ServiceState.IDLE

        manager._state = ServiceState.RUNNING
        assert manager.status == ServiceState.RUNNING

    @pytest.mark.asyncio
    async def test_lifespan_context(self):
        """Test lifespan context manager."""
        manager = LifecycleManager()
        service = MockService()
        manager.add_service(service)

        async with manager.lifespan():
            # Service should be started
            assert service.started is True
            assert manager._state == ServiceState.RUNNING

        # Service should be stopped after context
        assert service.stopped is True
        assert manager._state == ServiceState.STOPPED

    @pytest.mark.asyncio
    async def test_fastapi_lifespan(self):
        """Test FastAPI lifespan function."""
        manager = LifecycleManager()
        service = MockService()
        manager.add_service(service)

        app = FastAPI()
        lifespan_func = manager.fastapi_lifespan()

        # Simulate FastAPI lifespan
        async with lifespan_func(app):
            # Service should be started
            assert service.started is True

        # Service should be stopped
        assert service.stopped is True

    @pytest.mark.asyncio
    async def test_fastapi_lifespan_with_setup_handler(self):
        """Test FastAPI lifespan with setup handler."""
        manager = LifecycleManager()

        async def setup():
            return [MockService("Dynamic")]

        app = FastAPI()
        lifespan_func = manager.fastapi_lifespan(setup_handler=setup)

        # Simulate FastAPI lifespan
        async with lifespan_func(app):
            # Service from setup should be started
            assert len(manager._services) == 1
            assert manager._services[0].started is True

    @pytest.mark.asyncio
    async def test_handle_shutdown(self):
        """Test shutdown signal handling."""
        manager = LifecycleManager()
        service = MockService()
        manager.add_service(service)

        await manager.start()
        assert manager._state == ServiceState.RUNNING

        # Simulate shutdown signal
        await manager._handle_shutdown(signal.SIGTERM)

        assert manager._state == ServiceState.STOPPED
        assert service.stopped is True


class TestServiceState:
    """Test ServiceState enum."""

    def test_service_state_values(self):
        """Test all service state values exist."""
        assert ServiceState.IDLE == "idle"
        assert ServiceState.STARTING == "starting"
        assert ServiceState.RUNNING == "running"
        assert ServiceState.STOPPING == "stopping"
        assert ServiceState.STOPPED == "stopped"
        assert ServiceState.FAILED == "failed"

    def test_service_state_string(self):
        """Test service state string representation."""
        assert str(ServiceState.IDLE) == "idle"
        assert str(ServiceState.RUNNING) == "running"
