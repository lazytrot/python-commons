"""
Unit tests for AWS credentials.

Tests AWSCredentials and credential providers.
"""

import pytest
import os
import tempfile
from pathlib import Path
from internal_aws.auth.credentials import (
    AWSCredentials,
    ExplicitCredentialProvider,
    EnvironmentCredentialProvider,
    ProfileCredentialProvider,
    DefaultCredentialProvider
)


class TestAWSCredentials:
    """Test AWSCredentials model."""

    def test_basic_credentials(self):
        """Test basic credentials creation."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )

        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert creds.session_token is None
        assert creds.region is None

    def test_credentials_with_session_token(self):
        """Test credentials with session token."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="FwoGZXIvYXdzEBY...SESSION_TOKEN"
        )

        assert creds.session_token == "FwoGZXIvYXdzEBY...SESSION_TOKEN"

    def test_credentials_with_region(self):
        """Test credentials with region."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="us-east-1"
        )

        assert creds.region == "us-east-1"

    def test_to_dict_basic(self):
        """Test to_dict with basic credentials."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        )

        result = creds.to_dict()

        assert result["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert result["aws_secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert "aws_session_token" not in result
        assert "region_name" not in result

    def test_to_dict_with_session_token(self):
        """Test to_dict with session token."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="SESSION_TOKEN"
        )

        result = creds.to_dict()

        assert result["aws_session_token"] == "SESSION_TOKEN"

    def test_to_dict_with_region(self):
        """Test to_dict with region."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            region="eu-west-1"
        )

        result = creds.to_dict()

        assert result["region_name"] == "eu-west-1"

    def test_repr_hides_secrets(self):
        """Test that repr doesn't expose secret values."""
        creds = AWSCredentials(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            session_token="SECRET_TOKEN"
        )

        repr_str = repr(creds)

        # Secret access key and session token should not be in repr
        assert "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY" not in repr_str
        assert "SECRET_TOKEN" not in repr_str
        # Access key ID is fine to show
        assert "AKIAIOSFODNN7EXAMPLE" in repr_str


class TestExplicitCredentialProvider:
    """Test ExplicitCredentialProvider."""

    def test_init(self):
        """Test initialization."""
        provider = ExplicitCredentialProvider(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="SECRET",
            region="us-west-2"
        )

        assert provider.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert provider.secret_access_key == "SECRET"
        assert provider.region == "us-west-2"

    @pytest.mark.asyncio
    async def test_get_credentials(self):
        """Test getting credentials."""
        provider = ExplicitCredentialProvider(
            access_key_id="AKIAIOSFODNN7EXAMPLE",
            secret_access_key="SECRET",
            session_token="TOKEN",
            region="us-east-1"
        )

        creds = await provider.get_credentials()

        assert isinstance(creds, AWSCredentials)
        assert creds.access_key_id == "AKIAIOSFODNN7EXAMPLE"
        assert creds.secret_access_key == "SECRET"
        assert creds.session_token == "TOKEN"
        assert creds.region == "us-east-1"


class TestEnvironmentCredentialProvider:
    """Test EnvironmentCredentialProvider."""

    @pytest.mark.asyncio
    async def test_get_credentials_from_env(self, monkeypatch):
        """Test getting credentials from environment."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ENV_KEY_ID")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ENV_SECRET")
        monkeypatch.setenv("AWS_SESSION_TOKEN", "ENV_TOKEN")
        monkeypatch.setenv("AWS_DEFAULT_REGION", "us-west-2")

        provider = EnvironmentCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is not None
        assert creds.access_key_id == "ENV_KEY_ID"
        assert creds.secret_access_key == "ENV_SECRET"
        assert creds.session_token == "ENV_TOKEN"
        assert creds.region == "us-west-2"

    @pytest.mark.asyncio
    async def test_get_credentials_missing_env(self, monkeypatch):
        """Test when environment variables are missing."""
        # Clear any existing AWS env vars
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        provider = EnvironmentCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is None

    @pytest.mark.asyncio
    async def test_get_credentials_partial_env(self, monkeypatch):
        """Test with only some environment variables set."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "KEY")
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        provider = EnvironmentCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is None


class TestProfileCredentialProvider:
    """Test ProfileCredentialProvider."""

    def test_init(self):
        """Test initialization."""
        provider = ProfileCredentialProvider(profile_name="production")
        assert provider.profile_name == "production"

    def test_init_default(self):
        """Test initialization with default profile."""
        provider = ProfileCredentialProvider()
        assert provider.profile_name == "default"

    @pytest.mark.asyncio
    async def test_get_credentials_no_file(self, monkeypatch):
        """Test when credentials file doesn't exist."""
        # Use a non-existent home directory
        fake_home = Path("/nonexistent")
        monkeypatch.setattr(Path, "home", lambda: fake_home)

        provider = ProfileCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is None

    @pytest.mark.asyncio
    async def test_get_credentials_profile_not_found(self, tmp_path, monkeypatch):
        """Test when profile doesn't exist in credentials file."""
        # Create fake AWS directory
        aws_dir = tmp_path / ".aws"
        aws_dir.mkdir()
        creds_file = aws_dir / "credentials"
        creds_file.write_text("[default]\naws_access_key_id = AKIAEXAMPLE\naws_secret_access_key = SECRET\n")

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        provider = ProfileCredentialProvider(profile_name="nonexistent")
        creds = await provider.get_credentials()

        assert creds is None

    @pytest.mark.asyncio
    async def test_get_credentials_success(self, tmp_path, monkeypatch):
        """Test successful credential retrieval from profile."""
        # Create fake AWS directory
        aws_dir = tmp_path / ".aws"
        aws_dir.mkdir()
        creds_file = aws_dir / "credentials"
        creds_file.write_text(
            "[default]\n"
            "aws_access_key_id = DEFAULT_KEY\n"
            "aws_secret_access_key = DEFAULT_SECRET\n"
            "\n"
            "[production]\n"
            "aws_access_key_id = PROD_KEY\n"
            "aws_secret_access_key = PROD_SECRET\n"
            "aws_session_token = PROD_TOKEN\n"
            "region = us-east-1\n"
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        provider = ProfileCredentialProvider(profile_name="production")
        creds = await provider.get_credentials()

        assert creds is not None
        assert creds.access_key_id == "PROD_KEY"
        assert creds.secret_access_key == "PROD_SECRET"
        assert creds.session_token == "PROD_TOKEN"
        assert creds.region == "us-east-1"


class TestDefaultCredentialProvider:
    """Test DefaultCredentialProvider."""

    def test_init(self):
        """Test initialization."""
        provider = DefaultCredentialProvider(profile_name="dev")
        assert provider.profile_name == "dev"

    @pytest.mark.asyncio
    async def test_get_credentials_from_env(self, monkeypatch):
        """Test getting credentials from environment (first priority)."""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "ENV_KEY")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "ENV_SECRET")

        provider = DefaultCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is not None
        assert creds.access_key_id == "ENV_KEY"

    @pytest.mark.asyncio
    async def test_get_credentials_from_profile(self, tmp_path, monkeypatch):
        """Test getting credentials from profile when env not available."""
        # Clear env vars
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        # Create fake AWS directory
        aws_dir = tmp_path / ".aws"
        aws_dir.mkdir()
        creds_file = aws_dir / "credentials"
        creds_file.write_text(
            "[default]\n"
            "aws_access_key_id = PROFILE_KEY\n"
            "aws_secret_access_key = PROFILE_SECRET\n"
        )

        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        provider = DefaultCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is not None
        assert creds.access_key_id == "PROFILE_KEY"

    @pytest.mark.asyncio
    async def test_get_credentials_none_found(self, monkeypatch):
        """Test when no credentials found."""
        # Clear env vars
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        # Use non-existent home
        monkeypatch.setattr(Path, "home", lambda: Path("/nonexistent"))

        provider = DefaultCredentialProvider()
        creds = await provider.get_credentials()

        assert creds is None
