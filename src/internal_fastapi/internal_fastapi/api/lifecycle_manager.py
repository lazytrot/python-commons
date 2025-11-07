"""
Service lifecycle manager for FastAPI.

Provides lifecycle management with signal handling and service coordination.
"""

import asyncio
import signal
import logging
from typing import List, Callable, Awaitable, Optional, AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from internal_base import BackgroundServiceProtocol, ServiceState


logger = logging.getLogger(__name__)


class LifecycleManager:
    """
    Service lifecycle manager for FastAPI.

    Manages startup and shutdown of background services with signal handling.
    Integrates with FastAPI's lifespan context for proper resource management.

    Example:
        from fastapi import FastAPI
        from internal_fastapi import LifecycleManager
        from internal_base import AsyncService

        class MyBackgroundService(AsyncService):
            async def _start(self) -> None:
                print("Service starting...")

            async def _stop(self) -> None:
                print("Service stopping...")

            async def _health_check(self) -> bool:
                return True

        # Create lifecycle manager
        manager = LifecycleManager()

        # Add services
        service = MyBackgroundService()
        manager.add_service(service)

        # Create FastAPI app with lifespan
        app = FastAPI(lifespan=manager.fastapi_lifespan())

        # Or use with setup handler
        async def setup_services():
            service = MyBackgroundService()
            return [service]

        app = FastAPI(lifespan=manager.fastapi_lifespan(setup_services))
    """

    def __init__(self):
        """
        Initialize lifecycle manager.

        Example:
            manager = LifecycleManager()
        """
        self._services: List[BackgroundServiceProtocol] = []
        self._setup_handler: Optional[Callable[[], Awaitable[List[BackgroundServiceProtocol]]]] = None
        self._state = ServiceState.IDLE

    def add_service(self, service: BackgroundServiceProtocol) -> None:
        """
        Add a service to be managed.

        Args:
            service: Service implementing BackgroundServiceProtocol

        Example:
            manager = LifecycleManager()
            service = MyBackgroundService()
            manager.add_service(service)
        """
        self._services.append(service)
        logger.info(f"Added service: {service}")

    def set_setup_handler(
        self,
        handler: Callable[[], Awaitable[List[BackgroundServiceProtocol]]]
    ) -> None:
        """
        Set setup handler for dynamic service creation.

        Args:
            handler: Async function that returns list of services

        Example:
            async def setup_services():
                service1 = MyService1()
                service2 = MyService2()
                return [service1, service2]

            manager = LifecycleManager()
            manager.set_setup_handler(setup_services)
        """
        self._setup_handler = handler

    async def _handle_shutdown(self, sig: signal.Signals) -> None:
        """
        Handle shutdown signal.

        Args:
            sig: Signal received

        Example:
            # Called automatically when SIGTERM/SIGINT received
            await manager._handle_shutdown(signal.SIGTERM)
        """
        logger.info(f"Received signal {sig.name}, shutting down...")
        await self.stop()

    async def start(self) -> None:
        """
        Start all managed services.

        Calls setup handler if configured, then starts all services in order.

        Example:
            manager = LifecycleManager()
            manager.add_service(service1)
            manager.add_service(service2)
            await manager.start()
        """
        if self._state in (ServiceState.STARTING, ServiceState.RUNNING):
            logger.warning("Services already starting or running")
            return

        self._state = ServiceState.STARTING
        logger.info("Starting lifecycle manager...")

        try:
            # Call setup handler if configured
            if self._setup_handler:
                logger.info("Calling setup handler...")
                services = await self._setup_handler()
                self._services.extend(services)

            # Start all services
            for service in self._services:
                logger.info(f"Starting service: {service}")
                await service.start()

            self._state = ServiceState.RUNNING
            logger.info(f"Started {len(self._services)} services")

        except Exception as e:
            self._state = ServiceState.FAILED
            logger.error(f"Failed to start services: {e}", exc_info=True)
            raise

    async def stop(self) -> None:
        """
        Stop all managed services.

        Stops services in reverse order to handle dependencies correctly.

        Example:
            await manager.stop()
        """
        if self._state in (ServiceState.STOPPING, ServiceState.STOPPED):
            logger.warning("Services already stopping or stopped")
            return

        self._state = ServiceState.STOPPING
        logger.info("Stopping lifecycle manager...")

        # Stop services in reverse order
        for service in reversed(self._services):
            try:
                logger.info(f"Stopping service: {service}")
                await service.stop()
            except Exception as e:
                logger.error(f"Error stopping service {service}: {e}", exc_info=True)

        self._state = ServiceState.STOPPED
        logger.info("All services stopped")

    @property
    def status(self) -> ServiceState:
        """
        Get current lifecycle manager status.

        Returns:
            Current service state

        Example:
            if manager.status == ServiceState.RUNNING:
                print("Manager is running")
        """
        return self._state

    @asynccontextmanager
    async def lifespan(self) -> AsyncIterator[None]:
        """
        Lifespan context manager.

        Manages startup and shutdown within an async context.

        Yields:
            None

        Example:
            async with manager.lifespan():
                # Services are running
                await do_work()
                # Services will be stopped on exit
        """
        await self.start()
        try:
            yield
        finally:
            await self.stop()

    def fastapi_lifespan(
        self,
        setup_handler: Optional[Callable[[], Awaitable[List[BackgroundServiceProtocol]]]] = None
    ) -> Callable[[FastAPI], AsyncIterator[None]]:
        """
        Create FastAPI lifespan function.

        Returns a lifespan function compatible with FastAPI's lifespan parameter.

        Args:
            setup_handler: Optional setup handler for dynamic service creation

        Returns:
            Lifespan function for FastAPI

        Example:
            # Simple usage
            manager = LifecycleManager()
            manager.add_service(service1)
            manager.add_service(service2)

            app = FastAPI(lifespan=manager.fastapi_lifespan())

            # With setup handler
            async def setup_services():
                service = MyService()
                await service.initialize()
                return [service]

            manager = LifecycleManager()
            app = FastAPI(lifespan=manager.fastapi_lifespan(setup_handler=setup_services))

            # Manual signal handling
            import signal

            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(manager._handle_shutdown(s))
                )
        """
        if setup_handler:
            self.set_setup_handler(setup_handler)

        @asynccontextmanager
        async def _lifespan(app: FastAPI) -> AsyncIterator[None]:
            # Setup signal handlers
            loop = asyncio.get_event_loop()
            registered_signals = []

            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig,
                    lambda s=sig: asyncio.create_task(self._handle_shutdown(s))
                )
                registered_signals.append(sig)

            # Start services
            await self.start()

            try:
                yield
            finally:
                # Remove signal handlers
                for sig in registered_signals:
                    try:
                        loop.remove_signal_handler(sig)
                    except (ValueError, RuntimeError):
                        # Signal handler might already be removed or loop closed
                        pass

                # Stop services
                await self.stop()

        return _lifespan
