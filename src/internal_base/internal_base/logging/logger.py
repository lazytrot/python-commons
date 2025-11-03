"""
Logging utilities.

Provides functions for logger configuration and retrieval.
"""

import logging
from typing import Optional
import coloredlogs
from pythonjsonlogger import jsonlogger

from .config import LoggingConfig, LogFormat


def getLogger(name: str) -> logging.Logger:
    """
    Get a logger instance by name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Logger instance

    Example:
        from internal_base.logging import getLogger

        logger = getLogger(__name__)
        logger.info("Hello from my module")
    """
    return logging.getLogger(name)


def configure_logging(logger_settings: Optional[LoggingConfig] = None) -> None:
    """
    Configure logging for the application.

    Args:
        logger_settings: Logging configuration (uses defaults if None)

    Example:
        from internal_base.logging import configure_logging, LoggingConfig, LogFormat

        # Simple configuration
        configure_logging()

        # Custom configuration
        config = LoggingConfig(
            format=LogFormat.JSON,
            level="DEBUG",
            propagate=False
        )
        configure_logging(config)
    """
    if logger_settings is None:
        logger_settings = LoggingConfig()

    # Convert string level to numeric
    if isinstance(logger_settings.level, str):
        numeric_level = getattr(logging, logger_settings.level.upper(), logging.INFO)
    else:
        numeric_level = logger_settings.level

    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.propagate = logger_settings.propagate

    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create handler
    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)

    # Set formatter based on format
    if logger_settings.format == LogFormat.JSON:
        formatter = jsonlogger.JsonFormatter(
            "%(asctime)s %(name)s %(levelname)s %(message)s"
        )
    else:
        formatter = coloredlogs.ColoredFormatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

    handler.setFormatter(formatter)
    root_logger.addHandler(handler)

    # Install coloredlogs for text format
    if logger_settings.format == LogFormat.TEXT:
        coloredlogs.install(
            level=numeric_level,
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
