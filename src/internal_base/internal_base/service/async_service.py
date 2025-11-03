"""
Abstract base class for async services.

Provides a base implementation for background services with lifecycle management.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Optional

from .protocol import ServiceState


logger = logging.getLogger(__name__)


class AsyncService(ABC):
    """
    Abstract base class for async services.

    Provides lifecycle management (start/stop), health checking,
    and context manager support.

    Example:
        class MyBackgroundService(AsyncService):
            async def _start(self) -> None:
                # Initialize resources
                self.connection = await connect_to_database()

            async def _stop(self) -> None:
                # Cleanup resources
                await self.connection.close()

            async def _health_check(self) -> bool:
                # Check if service is healthy
                return await self.connection.ping()

        # Usage
        service = MyBackgroundService(name="db-service")

        await service.start()
        # ... service is running ...
        await service.stop()

        # Or use as context manager
        async with MyBackgroundService(name="db-service") as service:
            # Service automatically started
            await service.is_healthy()
            # Service automatically stopped on exit
    """

    def __init__(self, name: Optional[str] = None):
        """
        Initialize service.

        Args:
            name: Service name (defaults to class name)
        """
        self._name = name or self.__class__.__name__
        self._state = ServiceState.IDLE
        self._start_lock = asyncio.Lock()
        self._stop_lock = asyncio.Lock()

    @property
    def state(self) -> ServiceState:
        """Get current service state."""
        return self._state

    @property
    def name(self) -> str:
        """Get service name."""
        return self._name

    async def start(self) -> None:
        """
        Start the service.

        Raises:
            RuntimeError: If service is already running
        """
        async with self._start_lock:
            if self._state == ServiceState.RUNNING:
                logger.warning(f"Service '{self._name}' is already running")
                return

            if self._state not in (ServiceState.IDLE, ServiceState.STOPPED):
                raise RuntimeError(
                    f"Cannot start service '{self._name}' in state {self._state}"
                )

            logger.info(f"Starting service '{self._name}'...")
            self._state = ServiceState.STARTING

            try:
                await self._start()
                self._state = ServiceState.RUNNING
                logger.info(f"Service '{self._name}' started successfully")
            except Exception as e:
                self._state = ServiceState.FAILED
                logger.error(f"Failed to start service '{self._name}': {e}")
                raise

    async def stop(self) -> None:
        """
        Stop the service.

        Raises:
            RuntimeError: If service is not running
        """
        async with self._stop_lock:
            if self._state in (ServiceState.IDLE, ServiceState.STOPPED):
                logger.warning(f"Service '{self._name}' is not running")
                return

            if self._state != ServiceState.RUNNING:
                raise RuntimeError(
                    f"Cannot stop service '{self._name}' in state {self._state}"
                )

            logger.info(f"Stopping service '{self._name}'...")
            self._state = ServiceState.STOPPING

            try:
                await self._stop()
                self._state = ServiceState.STOPPED
                logger.info(f"Service '{self._name}' stopped successfully")
            except Exception as e:
                self._state = ServiceState.FAILED
                logger.error(f"Failed to stop service '{self._name}': {e}")
                raise

    async def is_healthy(self) -> bool:
        """
        Check if service is healthy.

        Returns:
            True if service is healthy and running
        """
        if self._state != ServiceState.RUNNING:
            return False

        try:
            return await self._health_check()
        except Exception as e:
            logger.error(f"Health check failed for service '{self._name}': {e}")
            return False

    async def __aenter__(self) -> "AsyncService":
        """Context manager entry - starts the service."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - stops the service."""
        await self.stop()

    # Abstract methods to be implemented by subclasses

    @abstractmethod
    async def _start(self) -> None:
        """
        Initialize and start the service.

        This method should set up any resources needed by the service.
        Called during start() lifecycle.

        Example:
            async def _start(self) -> None:
                self.db = await connect_to_database()
                self.cache = await connect_to_cache()
        """
        ...

    @abstractmethod
    async def _stop(self) -> None:
        """
        Stop and cleanup the service.

        This method should release any resources held by the service.
        Called during stop() lifecycle.

        Example:
            async def _stop(self) -> None:
                await self.db.close()
                await self.cache.close()
        """
        ...

    @abstractmethod
    async def _health_check(self) -> bool:
        """
        Perform health check.

        This method should verify that the service is functioning correctly.

        Returns:
            True if service is healthy, False otherwise

        Example:
            async def _health_check(self) -> bool:
                try:
                    await self.db.execute("SELECT 1")
                    return True
                except Exception:
                    return False
        """
        ...
