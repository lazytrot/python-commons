"""
Tests for internal_base logging module.

Tests LogFormat, LoggingConfig, getLogger, and configure_logging.
"""

import logging
import pytest
from internal_base import LogFormat, LoggingConfig, getLogger, configure_logging


class TestLogFormat:
    """Test LogFormat enum."""

    def test_log_format_values(self):
        """Test LogFormat enum values."""
        assert LogFormat.TEXT == "text"
        assert LogFormat.JSON == "json"

    def test_log_format_str(self):
        """Test LogFormat string representation."""
        assert str(LogFormat.TEXT) == "text"
        assert str(LogFormat.JSON) == "json"


class TestLoggingConfig:
    """Test LoggingConfig model."""

    def test_default_config(self):
        """Test default logging configuration."""
        config = LoggingConfig()
        assert config.format == LogFormat.TEXT
        assert config.level == "INFO"
        assert config.propagate is True

    def test_custom_config(self):
        """Test custom logging configuration."""
        config = LoggingConfig(
            format=LogFormat.JSON,
            level="DEBUG",
            propagate=False
        )
        assert config.format == LogFormat.JSON
        assert config.level == "DEBUG"
        assert config.propagate is False


class TestGetLogger:
    """Test getLogger function."""

    def test_get_logger_returns_logger(self):
        """Test that getLogger returns a logger instance."""
        logger = getLogger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    def test_get_logger_same_name_same_instance(self):
        """Test that same name returns same logger instance."""
        logger1 = getLogger("same_logger")
        logger2 = getLogger("same_logger")
        assert logger1 is logger2


class TestConfigureLogging:
    """Test configure_logging function."""

    def test_configure_logging_text_format(self):
        """Test configure_logging with TEXT format."""
        config = LoggingConfig(format=LogFormat.TEXT, level="DEBUG")
        configure_logging(config)

        # Verify root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_json_format(self):
        """Test configure_logging with JSON format."""
        config = LoggingConfig(format=LogFormat.JSON, level="INFO")
        configure_logging(config)

        # Verify root logger is configured
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_configure_logging_default(self):
        """Test configure_logging with default settings."""
        configure_logging()

        # Should use defaults
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO
