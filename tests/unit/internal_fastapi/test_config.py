"""
Unit tests for internal_fastapi configuration.

Tests APIConfig and Environment.
"""

import pytest
from internal_fastapi import APIConfig, Environment


class TestEnvironment:
    """Test Environment enum."""

    def test_environment_values(self):
        """Test environment enum values."""
        assert Environment.DEV == "dev"
        assert Environment.STAGE == "stage"
        assert Environment.PROD == "prod"

    def test_environment_str(self):
        """Test environment string representation."""
        assert str(Environment.DEV) == "dev"
        assert str(Environment.PROD) == "prod"


class TestAPIConfig:
    """Test APIConfig model."""

    def test_default_config(self):
        """Test default API configuration."""
        config = APIConfig()
        
        assert config.enabled is True
        assert config.env == Environment.DEV
        assert config.title == "Agent Framework API"
        assert config.host == "0.0.0.0"
        assert config.port == 8000
        assert config.reload is True
        assert config.workers == 1
        assert config.debug is True
        assert config.cors_origins == ["*"]

    def test_custom_config(self):
        """Test custom API configuration."""
        config = APIConfig(
            env=Environment.PROD,
            title="My API",
            version="2.0.0",
            host="127.0.0.1",
            port=9000,
            reload=False,
            workers=4,
            debug=False,
            cors_origins=["https://example.com"]
        )
        
        assert config.env == Environment.PROD
        assert config.title == "My API"
        assert config.version == "2.0.0"
        assert config.host == "127.0.0.1"
        assert config.port == 9000
        assert config.reload is False
        assert config.workers == 4
        assert config.debug is False
        assert config.cors_origins == ["https://example.com"]

    def test_port_validation(self):
        """Test port number validation."""
        # Valid ports
        config1 = APIConfig(port=1)
        config2 = APIConfig(port=65535)
        assert config1.port == 1
        assert config2.port == 65535
        
        # Invalid ports
        with pytest.raises(ValueError):
            APIConfig(port=0)
        
        with pytest.raises(ValueError):
            APIConfig(port=65536)

    def test_workers_validation(self):
        """Test workers validation."""
        # Valid
        config = APIConfig(workers=10)
        assert config.workers == 10
        
        # Invalid
        with pytest.raises(ValueError):
            APIConfig(workers=0)

    def test_production_config(self):
        """Test typical production configuration."""
        config = APIConfig(
            env=Environment.PROD,
            reload=False,
            workers=8,
            debug=False,
            cors_origins=["https://app.example.com", "https://www.example.com"]
        )
        
        assert config.env == Environment.PROD
        assert config.reload is False
        assert config.workers == 8
        assert config.debug is False
        assert len(config.cors_origins) == 2
