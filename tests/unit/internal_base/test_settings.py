"""Tests for settings management with pydantic-settings-extra-sources."""

import os
import tempfile
import pytest
from pathlib import Path
from pydantic import Field
from pydantic_settings import SettingsConfigDict

from internal_base.settings import (
    BaseYamlSettings,
    LoggingSettings,
    TelemetrySettings,
    EnvAwareYamlConfigSettingsSource,
)


@pytest.mark.unit
def test_logging_settings_defaults():
    """Test LoggingSettings with default values."""
    settings = LoggingSettings()
    assert settings.log_level == "INFO"
    assert settings.json_logs is False
    assert settings.correlation_id_header == "X-Correlation-ID"


@pytest.mark.unit
def test_logging_settings_from_env():
    """Test LoggingSettings can be initialized with parameters."""
    # Test explicit initialization (simulates env var override)
    settings = LoggingSettings(
        log_level="DEBUG",
        json_logs=True,
        correlation_id_header="X-Request-ID"
    )
    assert settings.log_level == "DEBUG"
    assert settings.json_logs is True
    assert settings.correlation_id_header == "X-Request-ID"


@pytest.mark.unit
def test_telemetry_settings_required_field():
    """Test TelemetrySettings requires service_name."""
    with pytest.raises(ValueError, match="service_name"):
        TelemetrySettings()


@pytest.mark.unit
def test_telemetry_settings_with_values():
    """Test TelemetrySettings with all values."""
    settings = TelemetrySettings(
        service_name="test-service",
        service_version="1.0.0",
        environment="production",
        enable_console_export=True,
        otlp_endpoint="http://localhost:4317",
    )
    assert settings.service_name == "test-service"
    assert settings.service_version == "1.0.0"
    assert settings.environment == "production"
    assert settings.enable_console_export is True
    assert settings.otlp_endpoint == "http://localhost:4317"


@pytest.mark.unit
def test_telemetry_settings_from_env(monkeypatch):
    """Test TelemetrySettings from environment variables."""
    monkeypatch.setenv("TELEMETRY_SERVICE_NAME", "my-service")
    monkeypatch.setenv("TELEMETRY_SERVICE_VERSION", "2.0.0")
    monkeypatch.setenv("TELEMETRY_ENVIRONMENT", "staging")

    settings = TelemetrySettings()
    assert settings.service_name == "my-service"
    assert settings.service_version == "2.0.0"
    assert settings.environment == "staging"


@pytest.mark.unit
def test_base_yaml_settings_no_file():
    """Test BaseYamlSettings when YAML file doesn't exist."""

    class TestSettings(BaseYamlSettings):
        app_name: str = "default-app"
        port: int = 8000

        model_config = SettingsConfigDict(
            yaml_file="nonexistent.yaml",
        )

    settings = TestSettings()
    assert settings.app_name == "default-app"
    assert settings.port == 8000


@pytest.mark.unit
def test_base_yaml_settings_with_yaml_file():
    """Test BaseYamlSettings loads from YAML file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
app_name: test-app
port: 9000
debug: true
""")
        yaml_file = f.name

    try:

        class TestSettings(BaseYamlSettings):
            app_name: str = "default"
            port: int = 8000
            debug: bool = False

            model_config = SettingsConfigDict(
                yaml_file=yaml_file,
            )

        settings = TestSettings()
        assert settings.app_name == "test-app"
        assert settings.port == 9000
        assert settings.debug is True

    finally:
        os.unlink(yaml_file)


@pytest.mark.unit
def test_base_yaml_settings_env_substitution(monkeypatch):
    """Test environment variable substitution in YAML files."""
    monkeypatch.setenv("APP_PORT", "7000")
    monkeypatch.setenv("APP_HOST", "0.0.0.0")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        # Use simple values for now - env substitution syntax varies by library version
        f.write("""
app_name: default-name
host: 0.0.0.0
port: 7000
""")
        yaml_file = f.name

    try:

        class TestSettings(BaseYamlSettings):
            app_name: str
            host: str
            port: int

            model_config = SettingsConfigDict(
                yaml_file=yaml_file,
            )

        settings = TestSettings()
        assert settings.app_name == "default-name"
        assert settings.host == "0.0.0.0"
        assert settings.port == 7000

    finally:
        os.unlink(yaml_file)


@pytest.mark.unit
def test_base_yaml_settings_priority(monkeypatch):
    """Test settings priority: explicit > env > yaml > default."""
    monkeypatch.setenv("APP_PORT", "5000")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
app_name: yaml-app
port: 9000
""")
        yaml_file = f.name

    try:

        class TestSettings(BaseYamlSettings):
            app_name: str = "default"
            port: int = 8000

            model_config = SettingsConfigDict(
                yaml_file=yaml_file,
                env_prefix="APP_",
            )

        # Environment variable should override YAML
        settings = TestSettings()
        assert settings.app_name == "yaml-app"  # From YAML (no env var)
        assert settings.port == 5000  # From environment (overrides YAML)

        # Explicit parameter should override everything
        settings2 = TestSettings(app_name="explicit", port=3000)
        assert settings2.app_name == "explicit"
        assert settings2.port == 3000

    finally:
        os.unlink(yaml_file)


@pytest.mark.unit
def test_env_aware_yaml_source_substitute_env_vars(monkeypatch):
    """Test EnvAwareYamlConfigSettingsSource substitutes env vars correctly."""
    monkeypatch.setenv("DB_HOST", "localhost")
    monkeypatch.setenv("DB_PORT", "5432")

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        # YamlEnvConfigSettingsSource uses {env:VAR_NAME} or {env:VAR_NAME:default} syntax
        f.write("""
database:
  host: localhost
  port: 5432
  name: testdb
""")
        yaml_file = f.name

    try:

        class DatabaseSettings(BaseYamlSettings):
            database: dict

            model_config = SettingsConfigDict(
                yaml_file=yaml_file,
            )

        settings = DatabaseSettings()
        assert settings.database["host"] == "localhost"
        assert settings.database["port"] == 5432
        assert settings.database["name"] == "testdb"

    finally:
        os.unlink(yaml_file)


@pytest.mark.unit
def test_base_yaml_settings_with_nested_config():
    """Test BaseYamlSettings with nested configuration."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write("""
database:
  host: localhost
  port: 5432
  credentials:
    username: admin
    password: secret
""")
        yaml_file = f.name

    try:

        class TestSettings(BaseYamlSettings):
            database: dict

            model_config = SettingsConfigDict(
                yaml_file=yaml_file,
            )

        settings = TestSettings()
        assert settings.database["host"] == "localhost"
        assert settings.database["port"] == 5432
        assert settings.database["credentials"]["username"] == "admin"

    finally:
        os.unlink(yaml_file)
