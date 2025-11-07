"""
Additional tests for logging module edge cases.

Tests uncovered edge cases in logger.py.
"""

import pytest
import logging
from internal_base.logging.logger import getLogger, configure_logging
from internal_base.logging.config import LoggingConfig, LogFormat


class TestLoggerEdgeCases:
    """Test edge cases in logger module."""

    def test_get_logger_caching(self):
        """Test that getLogger caches logger instances."""
        logger1 = getLogger("test.module")
        logger2 = getLogger("test.module")

        # Should return same instance
        assert logger1 is logger2

    def test_get_logger_different_names(self):
        """Test getLogger with different names."""
        logger1 = getLogger("module1")
        logger2 = getLogger("module2")

        # Should return different instances
        assert logger1 is not logger2
        assert logger1.name == "module1"
        assert logger2.name == "module2"

    def test_configure_logging_with_custom_level(self):
        """Test configure_logging with different log levels."""
        config = LoggingConfig(level="DEBUG")
        configure_logging(config)

        # Verify root logger level
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_configure_logging_text_format(self):
        """Test configure_logging with text format."""
        config = LoggingConfig(format=LogFormat.TEXT)
        configure_logging(config)

        # Should complete without error
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_configure_logging_json_format(self):
        """Test configure_logging with JSON format."""
        config = LoggingConfig(format=LogFormat.JSON)
        configure_logging(config)

        # Should complete without error
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0

    def test_configure_logging_default_config(self):
        """Test configure_logging with default config (None)."""
        configure_logging(None)

        # Should complete without error
        root_logger = logging.getLogger()
        assert len(root_logger.handlers) > 0
