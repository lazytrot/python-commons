"""
HTTP client with retry and auth support.

Provides async HTTP client with authentication, retry logic, and Pydantic model support.
"""

import asyncio
import logging
import random
from typing import Optional, Dict, Any, Union, Type, TypeVar
import httpx
from pydantic import BaseModel

from ..models.config import RetryConfig, AuthConfig


logger = logging.getLogger(__name__)

T = TypeVar('T', bound=BaseModel)


class HttpClientError(Exception):
    """HTTP client exception."""

    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        response: Optional[httpx.Response] = None
    ):
        """
        Initialize HTTP client error.

        Args:
            message: Error message
            status_code: HTTP status code if available
            response: HTTP response if available
        """
        super().__init__(message)
        self.status_code = status_code
        self.response = response


class HttpClient:
    """
    Async HTTP client with retry and auth support.

    Example:
        from internal_http import HttpClient, BearerAuth, AuthConfig, RetryConfig

        # Simple usage
        async with HttpClient(base_url="https://api.example.com") as client:
            response = await client.get("/users")
            print(response.json())

        # With authentication
        auth_config = AuthConfig(auth=BearerAuth("token"))
        client = HttpClient(
            base_url="https://api.example.com",
            auth_config=auth_config
        )
        await client.get("/protected")

        # With retries and Pydantic models
        from pydantic import BaseModel

        class User(BaseModel):
            id: int
            name: str

        user = await client.get_model("/users/1", User)
        print(user.name)
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: Union[float, httpx.Timeout] = 10.0,
        retries: Optional[Union[int, RetryConfig]] = None,
        auth_config: Optional[AuthConfig] = None,
        default_headers: Optional[Dict[str, str]] = None,
        verify_ssl: bool = True,
        follow_redirects: bool = True,
    ):
        """
        Initialize HTTP client.

        Args:
            base_url: Base URL for all requests
            timeout: Request timeout (seconds or httpx.Timeout)
            retries: Retry configuration (int for simple retry count, or RetryConfig)
            auth_config: Authentication configuration
            default_headers: Default headers for all requests
            verify_ssl: Verify SSL certificates
            follow_redirects: Follow HTTP redirects
        """
        self.base_url = base_url
        self.timeout = timeout if isinstance(timeout, httpx.Timeout) else httpx.Timeout(timeout)
        self.auth_config = auth_config or AuthConfig()
        self.default_headers = default_headers or {}
        self.verify_ssl = verify_ssl
        self.follow_redirects = follow_redirects

        # Setup retry config
        if isinstance(retries, int):
            self.retry_config = RetryConfig(max_attempts=retries)
        elif isinstance(retries, RetryConfig):
            self.retry_config = retries
        elif retries is None:
            self.retry_config = RetryConfig()
        else:
            self.retry_config = RetryConfig()

        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        """Context manager entry."""
        await self._ensure_client()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()

    async def close(self):
        """Close the HTTP client and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None

    async def _ensure_client(self) -> httpx.AsyncClient:
        """Ensure client is created."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                verify=self.verify_ssl,
                follow_redirects=self.follow_redirects,
            )
        return self._client

    @property
    async def client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        return await self._ensure_client()

    def _should_retry(self, response: httpx.Response) -> bool:
        """
        Check if request should be retried based on response.

        Args:
            response: HTTP response

        Returns:
            True if should retry
        """
        return response.status_code in self.retry_config.retry_statuses

    def _prepare_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> Dict[str, Any]:
        """
        Prepare request with headers and auth.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            **kwargs: Additional request parameters

        Returns:
            Prepared request parameters
        """
        # Merge headers
        merged_headers = {**self.default_headers}
        if headers:
            merged_headers.update(headers)

        # Apply auth if configured
        if self.auth_config.auth:
            # Create a temporary request to apply auth
            temp_request = httpx.Request(method, url, headers=merged_headers)
            temp_request = self.auth_config.auth.auth_flow(temp_request)
            merged_headers = dict(temp_request.headers)

        return {
            "method": method,
            "url": url,
            "headers": merged_headers,
            **kwargs
        }

    async def _execute_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """
        Execute HTTP request with retry logic.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            **kwargs: Additional request parameters

        Returns:
            HTTP response

        Raises:
            HttpClientError: On request failure
        """
        client = await self.client
        request_params = self._prepare_request(method, url, headers, **kwargs)

        last_exception = None
        backoff = self.retry_config.backoff_factor

        for attempt in range(self.retry_config.max_attempts):
            try:
                response = await client.request(**request_params)

                # Check if we should retry based on status code
                if self._should_retry(response) and attempt < self.retry_config.max_attempts - 1:
                    # Calculate backoff with jitter
                    wait_time = backoff * (2 ** attempt)
                    if self.retry_config.jitter:
                        wait_time *= (0.5 + random.random())

                    logger.warning(
                        f"Request failed with status {response.status_code}, "
                        f"retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.retry_config.max_attempts})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                return response

            except Exception as e:
                last_exception = e
                if attempt < self.retry_config.max_attempts - 1:
                    wait_time = backoff * (2 ** attempt)
                    if self.retry_config.jitter:
                        wait_time *= (0.5 + random.random())

                    logger.warning(
                        f"Request failed with exception: {e}, "
                        f"retrying in {wait_time:.2f}s (attempt {attempt + 1}/{self.retry_config.max_attempts})"
                    )
                    await asyncio.sleep(wait_time)
                    continue

                raise HttpClientError(f"Request failed: {e}") from e

        # All retries exhausted
        if last_exception:
            raise HttpClientError(f"Request failed after {self.retry_config.max_attempts} attempts") from last_exception

        raise HttpClientError(f"Request failed after {self.retry_config.max_attempts} attempts")

    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """
        Make HTTP request.

        Args:
            method: HTTP method
            url: Request URL
            headers: Request headers
            **kwargs: Additional request parameters

        Returns:
            HTTP response
        """
        return await self._execute_request(method, url, headers, **kwargs)

    async def get(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """Make GET request."""
        return await self.request("GET", url, headers, **kwargs)

    async def post(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """Make POST request."""
        return await self.request("POST", url, headers, **kwargs)

    async def put(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """Make PUT request."""
        return await self.request("PUT", url, headers, **kwargs)

    async def patch(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """Make PATCH request."""
        return await self.request("PATCH", url, headers, **kwargs)

    async def delete(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> httpx.Response:
        """Make DELETE request."""
        return await self.request("DELETE", url, headers, **kwargs)

    async def get_model(
        self,
        url: str,
        response_model: Type[T],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> T:
        """
        Make GET request and parse response into Pydantic model.

        Args:
            url: Request URL
            response_model: Pydantic model class
            headers: Request headers
            **kwargs: Additional request parameters

        Returns:
            Parsed Pydantic model instance
        """
        response = await self.get(url, headers, **kwargs)
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def post_model(
        self,
        url: str,
        response_model: Type[T],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> T:
        """Make POST request and parse response into Pydantic model."""
        response = await self.post(url, headers, **kwargs)
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def put_model(
        self,
        url: str,
        response_model: Type[T],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> T:
        """Make PUT request and parse response into Pydantic model."""
        response = await self.put(url, headers, **kwargs)
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def patch_model(
        self,
        url: str,
        response_model: Type[T],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> T:
        """Make PATCH request and parse response into Pydantic model."""
        response = await self.patch(url, headers, **kwargs)
        response.raise_for_status()
        return response_model.model_validate(response.json())

    async def delete_model(
        self,
        url: str,
        response_model: Type[T],
        headers: Optional[Dict[str, str]] = None,
        **kwargs: Any
    ) -> T:
        """Make DELETE request and parse response into Pydantic model."""
        response = await self.delete(url, headers, **kwargs)
        response.raise_for_status()
        return response_model.model_validate(response.json())
