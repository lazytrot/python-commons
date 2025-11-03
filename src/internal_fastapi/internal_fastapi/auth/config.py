"""
Authentication configuration models.

Provides configuration for app token authentication.
"""

from typing import Dict, Set
from pydantic import BaseModel, Field, field_validator


class AppTokenConfig(BaseModel):
    """
    App token authentication configuration.

    Configuration for token-based authentication with path exclusions.

    Example:
        from internal_fastapi import AppTokenConfig

        config = AppTokenConfig(
            header_name="X-API-Key",
            tokens={
                "service1": "secret-token-1",
                "service2": "secret-token-2",
                "admin": "admin-secret-token"
            },
            enabled=True,
            exclude_paths={
                "/health",
                "/docs",
                "/openapi.json",
                "/api/public/*"  # Glob pattern
            }
        )
    """

    header_name: str = Field(
        default="X-App-Token",
        description="HTTP header name for token"
    )
    tokens: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of app names to tokens"
    )
    enabled: bool = Field(
        default=True,
        description="Whether authentication is enabled"
    )
    exclude_paths: Set[str] = Field(
        default_factory=set,
        description="Paths to exclude from authentication (supports glob patterns)"
    )

    @field_validator("header_name")
    @classmethod
    def validate_header_name(cls, v: str) -> str:
        """
        Validate header name.

        Args:
            v: Header name

        Returns:
            Validated header name

        Raises:
            ValueError: If header name is empty

        Example:
            config = AppTokenConfig(header_name="X-API-Key")
        """
        if not v or not v.strip():
            raise ValueError("header_name cannot be empty")
        return v.strip()

    @field_validator("tokens")
    @classmethod
    def validate_tokens(cls, v: Dict[str, str]) -> Dict[str, str]:
        """
        Validate tokens.

        Args:
            v: Tokens dictionary

        Returns:
            Validated tokens

        Raises:
            ValueError: If tokens contain empty values

        Example:
            config = AppTokenConfig(
                tokens={"app1": "token1", "app2": "token2"}
            )
        """
        for app_name, token in v.items():
            if not token or not token.strip():
                raise ValueError(f"Token for '{app_name}' cannot be empty")
        return v
