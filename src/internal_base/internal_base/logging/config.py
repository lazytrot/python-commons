"""
Logging configuration models.

Provides configuration classes for logging setup.
"""

from enum import Enum
from pydantic import BaseModel


class LogFormat(str, Enum):
    """Logging format enumeration."""

    TEXT = "text"
    JSON = "json"

    def __str__(self) -> str:
        """Return string representation."""
        return self.value


class LoggingConfig(BaseModel):
    """Logging configuration model."""

    format: LogFormat = LogFormat.TEXT
    level: str = "INFO"
    propagate: bool = True
