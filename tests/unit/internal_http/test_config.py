"""
Unit tests for internal_http configuration models.

Tests RetryConfig and AuthConfig.
"""

import pytest
from internal_http import RetryConfig, AuthConfig, BearerAuth


class TestRetryConfig:
    """Test RetryConfig model."""

    def test_default_config(self):
        """Test default retry configuration."""
        config = RetryConfig()
        
        assert config.max_attempts == 3
        assert config.retry_statuses == [500, 502, 503, 504]
        assert config.retry_methods == ["GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]
        assert config.backoff_factor == 0.5
        assert config.jitter is True
        assert config.retry_exceptions == []

    def test_custom_config(self):
        """Test custom retry configuration."""
        config = RetryConfig(
            max_attempts=5,
            retry_statuses=[429, 500],
            backoff_factor=1.0,
            jitter=False
        )
        
        assert config.max_attempts == 5
        assert config.retry_statuses == [429, 500]
        assert config.backoff_factor == 1.0
        assert config.jitter is False

    def test_retry_methods_customization(self):
        """Test customizing retry methods."""
        config = RetryConfig(
            retry_methods=["GET", "POST"]
        )
        
        assert config.retry_methods == ["GET", "POST"]


class TestAuthConfig:
    """Test AuthConfig model."""

    def test_default_config(self):
        """Test default auth configuration."""
        config = AuthConfig()
        
        assert config.auth is None
        assert config.refresh_token is None
        assert config.refresh_callback is None

    def test_config_with_auth(self):
        """Test auth config with auth object."""
        auth = BearerAuth("token123")
        config = AuthConfig(auth=auth)
        
        assert config.auth == auth

    def test_config_with_refresh_token(self):
        """Test auth config with refresh token."""
        config = AuthConfig(refresh_token="refresh-token-123")
        
        assert config.refresh_token == "refresh-token-123"

    def test_config_with_refresh_callback(self):
        """Test auth config with refresh callback."""
        def refresh():
            return "new-token"
        
        config = AuthConfig(refresh_callback=refresh)
        
        assert config.refresh_callback == refresh
        assert config.refresh_callback() == "new-token"
