"""
Unit tests for internal_http authentication.

Tests all auth mechanisms.
"""

import pytest
import base64
from internal_http import AuthBase, BearerAuth, BasicAuth, ApiKeyAuth


class TestAuthBase:
    """Test AuthBase class."""

    def test_auth_base_default(self):
        """Test AuthBase default behavior."""
        auth = AuthBase()
        
        # Mock request
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        # Should return request unchanged
        assert result == request


class TestBearerAuth:
    """Test BearerAuth."""

    def test_bearer_auth_header(self):
        """Test Bearer token is added to headers."""
        auth = BearerAuth("my-secret-token")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert "Authorization" in result.headers
        assert result.headers["Authorization"] == "Bearer my-secret-token"

    def test_bearer_auth_different_tokens(self):
        """Test different tokens."""
        auth1 = BearerAuth("token1")
        auth2 = BearerAuth("token2")
        
        class MockRequest:
            headers = {}
        
        req1 = MockRequest()
        req2 = MockRequest()
        
        result1 = auth1.auth_flow(req1)
        result2 = auth2.auth_flow(req2)
        
        assert result1.headers["Authorization"] == "Bearer token1"
        assert result2.headers["Authorization"] == "Bearer token2"


class TestBasicAuth:
    """Test BasicAuth."""

    def test_basic_auth_header(self):
        """Test Basic auth header is correctly encoded."""
        auth = BasicAuth("username", "password")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert "Authorization" in result.headers
        
        # Decode and verify
        header = result.headers["Authorization"]
        assert header.startswith("Basic ")
        
        encoded = header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "username:password"

    def test_basic_auth_special_characters(self):
        """Test Basic auth with special characters."""
        auth = BasicAuth("user@example.com", "p@ssw0rd!")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        header = result.headers["Authorization"]
        encoded = header.split(" ")[1]
        decoded = base64.b64decode(encoded).decode()
        assert decoded == "user@example.com:p@ssw0rd!"


class TestApiKeyAuth:
    """Test ApiKeyAuth."""

    def test_api_key_default_header(self):
        """Test API key with default header name."""
        auth = ApiKeyAuth("my-api-key")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert "X-API-Key" in result.headers
        assert result.headers["X-API-Key"] == "my-api-key"

    def test_api_key_custom_header(self):
        """Test API key with custom header name."""
        auth = ApiKeyAuth("my-key", header_name="X-Custom-Key")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert "X-Custom-Key" in result.headers
        assert result.headers["X-Custom-Key"] == "my-key"

    def test_api_key_with_prefix(self):
        """Test API key with prefix."""
        auth = ApiKeyAuth("secret123", header_name="Authorization", prefix="ApiKey")
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert result.headers["Authorization"] == "ApiKey secret123"

    def test_api_key_without_prefix(self):
        """Test API key without prefix."""
        auth = ApiKeyAuth("secret456", header_name="X-API-Key", prefix=None)
        
        class MockRequest:
            headers = {}
        
        request = MockRequest()
        result = auth.auth_flow(request)
        
        assert result.headers["X-API-Key"] == "secret456"
