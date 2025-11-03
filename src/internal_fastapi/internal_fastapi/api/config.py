"""
API configuration models.

Provides configuration models for FastAPI applications.
"""

from enum import Enum
from typing import List
from pydantic import BaseModel, Field, field_validator


class Environment(str, Enum):
    """Environment enumeration."""

    DEV = "dev"
    STAGE = "stage"
    PROD = "prod"

    def __str__(self) -> str:
        """String representation."""
        return self.value


class APIConfig(BaseModel):
    """
    API configuration.

    Configuration model for FastAPI applications including server settings,
    CORS configuration, and environment-specific options.

    Example:
        from internal_fastapi import APIConfig, Environment

        # Development config
        config = APIConfig(
            enabled=True,
            env=Environment.DEV,
            title="My API",
            description="API for my application",
            version="1.0.0",
            host="0.0.0.0",
            port=8000,
            reload=True,
            debug=True,
            cors_origins=["http://localhost:3000"]
        )

        # Production config
        prod_config = APIConfig(
            enabled=True,
            env=Environment.PROD,
            title="My API",
            version="1.0.0",
            host="0.0.0.0",
            port=8000,
            reload=False,
            workers=4,
            debug=False,
            cors_origins=["https://myapp.com"]
        )
    """

    enabled: bool = Field(
        default=True,
        description="Whether the API is enabled"
    )
    env: Environment = Field(
        default=Environment.DEV,
        description="Environment (dev, stage, prod)"
    )
    title: str = Field(
        default="Agent Framework API",
        description="API title"
    )
    description: str = Field(
        default="API for interacting with the agent framework",
        description="API description"
    )
    version: str = Field(
        default="1.0.0",
        description="API version"
    )
    host: str = Field(
        default="0.0.0.0",
        description="Host to bind to"
    )
    port: int = Field(
        default=8000,
        description="Port to bind to"
    )
    reload: bool = Field(
        default=True,
        description="Enable auto-reload (development only)"
    )
    workers: int = Field(
        default=1,
        description="Number of worker processes"
    )
    debug: bool = Field(
        default=True,
        description="Enable debug mode"
    )
    cors_origins: List[str] = Field(
        default=["*"],
        description="CORS allowed origins"
    )

    @field_validator("port")
    @classmethod
    def validate_port(cls, v: int) -> int:
        """
        Validate port number.

        Args:
            v: Port value

        Returns:
            Validated port

        Raises:
            ValueError: If port is out of range
        """
        if not 1 <= v <= 65535:
            raise ValueError("Port must be between 1 and 65535")
        return v

    @field_validator("workers")
    @classmethod
    def validate_workers(cls, v: int) -> int:
        """
        Validate worker count.

        Args:
            v: Worker count

        Returns:
            Validated worker count

        Raises:
            ValueError: If worker count is invalid
        """
        if v < 1:
            raise ValueError("Workers must be at least 1")
        return v

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
