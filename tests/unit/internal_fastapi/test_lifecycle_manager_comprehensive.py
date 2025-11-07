"""
Comprehensive tests for lifecycle manager to achieve 100% coverage.

Tests uncovered lines including signal handling in FastAPI lifespan.
"""

import pytest
import asyncio
import signal
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi import FastAPI
from internal_fastapi.api.lifecycle_manager import LifecycleManager, ServiceState


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


@pytest.mark.asyncio
async def test_start_already_starting():
    """Test starting when already in STARTING state."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    # Set state to STARTING
    manager._state = ServiceState.STARTING

    # Try to start
    await manager.start()

    # Should not change state or start services again
    assert not service.started


@pytest.mark.asyncio
async def test_stop_when_stopping():
    """Test stopping when already in STOPPING state."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    await manager.start()

    # Set state to STOPPING
    manager._state = ServiceState.STOPPING

    # Try to stop
    await manager.stop()

    # Should not proceed
    assert manager._state == ServiceState.STOPPING


@pytest.mark.asyncio
async def test_fastapi_lifespan_with_signal_handlers():
    """Test FastAPI lifespan sets up signal handlers."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    app = FastAPI()
    lifespan_func = manager.fastapi_lifespan()

    # Mock the event loop and signal handler setup
    mock_loop = MagicMock()
    signal_handlers = {}

    def mock_add_signal_handler(sig, callback):
        signal_handlers[sig] = callback

    mock_loop.add_signal_handler = mock_add_signal_handler

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        async with lifespan_func(app):
            # Verify signal handlers were registered
            assert signal.SIGTERM in signal_handlers
            assert signal.SIGINT in signal_handlers

            # Service should be started
            assert service.started is True

        # Service should be stopped
        assert service.stopped is True


@pytest.mark.asyncio
async def test_fastapi_lifespan_signal_handler_lambda():
    """Test that signal handler lambdas are created correctly."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    app = FastAPI()
    lifespan_func = manager.fastapi_lifespan()

    # Track signal handler calls
    signal_handlers_called = []

    mock_loop = MagicMock()

    def mock_add_signal_handler(sig, callback):
        # Store the callback
        signal_handlers_called.append((sig, callback))

    mock_loop.add_signal_handler = mock_add_signal_handler

    # Mock create_task to properly handle coroutines
    def mock_create_task_func(coro):
        # Close the coroutine to avoid "never awaited" warning
        if asyncio.iscoroutine(coro):
            coro.close()
        return MagicMock()

    with patch("asyncio.get_event_loop", return_value=mock_loop):
        with patch("asyncio.create_task", side_effect=mock_create_task_func) as mock_create_task:
            async with lifespan_func(app):
                # Signal handlers should be registered
                assert len(signal_handlers_called) == 2

                # Get one of the callbacks
                sig, callback = signal_handlers_called[0]

                # Call the signal handler callback
                callback()

                # Should create task with _handle_shutdown
                assert mock_create_task.called

            # Service should be stopped
            assert service.stopped is True


@pytest.mark.asyncio
async def test_fastapi_lifespan_without_setup_handler():
    """Test FastAPI lifespan when no setup_handler is provided."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    app = FastAPI()

    # Don't pass setup_handler
    lifespan_func = manager.fastapi_lifespan(setup_handler=None)

    async with lifespan_func(app):
        # Service should be started
        assert service.started is True

    # Service should be stopped
    assert service.stopped is True


@pytest.mark.asyncio
async def test_lifespan_context_exception_handling():
    """Test lifespan context manager stops services even on exception."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    try:
        async with manager.lifespan():
            # Service should be started
            assert service.started is True
            # Raise exception
            raise ValueError("Test exception")
    except ValueError:
        pass

    # Service should still be stopped despite exception
    assert service.stopped is True
    assert manager._state == ServiceState.STOPPED


@pytest.mark.asyncio
async def test_fastapi_lifespan_exception_in_app():
    """Test FastAPI lifespan stops services even if exception in app."""
    manager = LifecycleManager()
    service = MockService()
    manager.add_service(service)

    app = FastAPI()
    lifespan_func = manager.fastapi_lifespan()

    try:
        async with lifespan_func(app):
            # Service should be started
            assert service.started is True
            # Raise exception
            raise RuntimeError("App error")
    except RuntimeError:
        pass

    # Service should still be stopped
    assert service.stopped is True
