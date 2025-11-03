"""
Authentication strategies for HTTP requests.

Provides various authentication mechanisms compatible with httpx.
"""

import base64
from typing import Optional
import httpx


class AuthBase:
    """Base authentication class."""

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """
        Apply authentication to request.

        Args:
            request: HTTP request

        Returns:
            Request with authentication applied

        Example:
            class CustomAuth(AuthBase):
                def auth_flow(self, request):
                    request.headers["X-Custom-Auth"] = "value"
                    return request
        """
        return request


class BearerAuth(AuthBase):
    """Bearer token authentication."""

    def __init__(self, token: str):
        """
        Initialize Bearer authentication.

        Args:
            token: Bearer token

        Example:
            from internal_http import HttpClient, BearerAuth

            auth = BearerAuth("your-api-token")
            client = HttpClient(
                base_url="https://api.example.com",
                auth_config=AuthConfig(auth=auth)
            )

            response = await client.get("/protected")
        """
        self.token = token

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """Apply Bearer token to Authorization header."""
        request.headers["Authorization"] = f"Bearer {self.token}"
        return request


class BasicAuth(AuthBase):
    """HTTP Basic authentication."""

    def __init__(self, username: str, password: str):
        """
        Initialize Basic authentication.

        Args:
            username: Username
            password: Password

        Example:
            from internal_http import HttpClient, BasicAuth

            auth = BasicAuth("user", "pass")
            client = HttpClient(
                base_url="https://api.example.com",
                auth_config=AuthConfig(auth=auth)
            )
        """
        self.username = username
        self.password = password

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """Apply Basic auth to Authorization header."""
        credentials = f"{self.username}:{self.password}"
        encoded = base64.b64encode(credentials.encode()).decode()
        request.headers["Authorization"] = f"Basic {encoded}"
        return request


class ApiKeyAuth(AuthBase):
    """API key authentication."""

    def __init__(
        self,
        api_key: str,
        header_name: str = "X-API-Key",
        prefix: Optional[str] = None,
    ):
        """
        Initialize API key authentication.

        Args:
            api_key: API key value
            header_name: Header name for the API key (default: X-API-Key)
            prefix: Optional prefix for the key value (e.g., "ApiKey")

        Example:
            # Simple API key
            auth = ApiKeyAuth("abc123")

            # API key with custom header
            auth = ApiKeyAuth("abc123", header_name="X-Custom-Key")

            # API key with prefix
            auth = ApiKeyAuth("abc123", prefix="ApiKey")
            # Results in header: X-API-Key: ApiKey abc123
        """
        self.api_key = api_key
        self.header_name = header_name
        self.prefix = prefix

    def auth_flow(self, request: httpx.Request) -> httpx.Request:
        """Apply API key to custom header."""
        value = f"{self.prefix} {self.api_key}" if self.prefix else self.api_key
        request.headers[self.header_name] = value
        return request
