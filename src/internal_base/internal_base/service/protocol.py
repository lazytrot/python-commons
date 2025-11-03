"""
Service protocol definitions.

Provides protocols and enums for async services.
"""

from enum import Enum
from typing import Protocol, runtime_checkable


class ServiceState(str, Enum):
    """Service state enumeration."""

    IDLE = "idle"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    STOPPED = "stopped"
    FAILED = "failed"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


@runtime_checkable
class BackgroundServiceProtocol(Protocol):
    """Protocol for background services (runtime_checkable)."""

    @property
    def state(self) -> ServiceState:
        """Get current service state."""
        ...

    async def start(self) -> None:
        """Start the service."""
        ...

    async def stop(self) -> None:
        """Stop the service."""
        ...

    async def is_healthy(self) -> bool:
        """Check if service is healthy."""
        ...
