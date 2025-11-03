"""
internal_base - Base utilities package.

Provides logging configuration, async service management, and more.
"""

from .logging import LogFormat, LoggingConfig, getLogger, configure_logging
from .service import ServiceState, BackgroundServiceProtocol, AsyncService

__all__ = [
    # Logging
    "LogFormat",
    "LoggingConfig",
    "getLogger",
    "configure_logging",
    # Service
    "ServiceState",
    "BackgroundServiceProtocol",
    "AsyncService",
]
