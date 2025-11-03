"""
AWS credentials management.

Provides credential providers for AWS authentication.
"""

import os
from abc import ABC, abstractmethod
from typing import Optional, Dict
from pydantic import BaseModel, Field


class AWSCredentials(BaseModel):
    """AWS credentials model."""

    access_key_id: str = Field(description="AWS access key ID")
    secret_access_key: str = Field(description="AWS secret access key", repr=False)
    session_token: Optional[str] = Field(default=None, description="AWS session token", repr=False)
    region: Optional[str] = Field(default=None, description="AWS region")

    def to_dict(self) -> Dict[str, str]:
        """
        Convert credentials to dictionary format.

        Returns:
            Dictionary with credentials

        Example:
            creds = AWSCredentials(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            )
            print(creds.to_dict())
            # {'aws_access_key_id': 'AKIA...', 'aws_secret_access_key': '...', ...}
        """
        result = {
            "aws_access_key_id": self.access_key_id,
            "aws_secret_access_key": self.secret_access_key,
        }
        if self.session_token:
            result["aws_session_token"] = self.session_token
        if self.region:
            result["region_name"] = self.region
        return result


class CredentialProvider(ABC):
    """Abstract credential provider."""

    @abstractmethod
    async def get_credentials(self) -> Optional[AWSCredentials]:
        """
        Get AWS credentials.

        Returns:
            AWSCredentials instance or None if credentials not available

        Example:
            provider = ExplicitCredentialProvider(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
            )
            creds = await provider.get_credentials()
        """
        pass


class ExplicitCredentialProvider(CredentialProvider):
    """Explicit credential provider with hardcoded values."""

    def __init__(
        self,
        access_key_id: str,
        secret_access_key: str,
        session_token: Optional[str] = None,
        region: Optional[str] = None
    ):
        """
        Initialize with explicit credentials.

        Args:
            access_key_id: AWS access key ID
            secret_access_key: AWS secret access key
            session_token: Optional session token
            region: Optional AWS region

        Example:
            provider = ExplicitCredentialProvider(
                access_key_id="AKIAIOSFODNN7EXAMPLE",
                secret_access_key="wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
                region="us-east-1"
            )
        """
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.session_token = session_token
        self.region = region

    async def get_credentials(self) -> AWSCredentials:
        """Get explicit credentials."""
        return AWSCredentials(
            access_key_id=self.access_key_id,
            secret_access_key=self.secret_access_key,
            session_token=self.session_token,
            region=self.region,
        )


class EnvironmentCredentialProvider(CredentialProvider):
    """Credential provider from environment variables."""

    async def get_credentials(self) -> Optional[AWSCredentials]:
        """
        Get credentials from environment variables.

        Looks for: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_SESSION_TOKEN, AWS_DEFAULT_REGION

        Returns:
            AWSCredentials or None if environment variables not set

        Example:
            # Set environment variables:
            # export AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
            # export AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY

            provider = EnvironmentCredentialProvider()
            creds = await provider.get_credentials()
        """
        access_key_id = os.getenv("AWS_ACCESS_KEY_ID")
        secret_access_key = os.getenv("AWS_SECRET_ACCESS_KEY")

        if not access_key_id or not secret_access_key:
            return None

        return AWSCredentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=os.getenv("AWS_SESSION_TOKEN"),
            region=os.getenv("AWS_DEFAULT_REGION"),
        )


class ProfileCredentialProvider(CredentialProvider):
    """Credential provider from AWS profile."""

    def __init__(self, profile_name: str = "default"):
        """
        Initialize with AWS profile name.

        Args:
            profile_name: AWS profile name from ~/.aws/credentials

        Example:
            provider = ProfileCredentialProvider(profile_name="production")
            creds = await provider.get_credentials()
        """
        self.profile_name = profile_name

    async def get_credentials(self) -> Optional[AWSCredentials]:
        """
        Get credentials from AWS profile.

        Reads from ~/.aws/credentials file.

        Returns:
            AWSCredentials or None if profile not found

        Example:
            provider = ProfileCredentialProvider(profile_name="dev")
            creds = await provider.get_credentials()
        """
        # This is a simplified implementation
        # In production, use boto3.Session(profile_name=self.profile_name).get_credentials()
        import configparser
        from pathlib import Path

        credentials_path = Path.home() / ".aws" / "credentials"
        if not credentials_path.exists():
            return None

        config = configparser.ConfigParser()
        config.read(credentials_path)

        if self.profile_name not in config:
            return None

        profile = config[self.profile_name]
        access_key_id = profile.get("aws_access_key_id")
        secret_access_key = profile.get("aws_secret_access_key")

        if not access_key_id or not secret_access_key:
            return None

        return AWSCredentials(
            access_key_id=access_key_id,
            secret_access_key=secret_access_key,
            session_token=profile.get("aws_session_token"),
            region=profile.get("region"),
        )


class DefaultCredentialProvider(CredentialProvider):
    """Default credential provider (tries multiple sources)."""

    def __init__(self, profile_name: str = "default"):
        """
        Initialize default credential provider.

        Tries credentials in order:
        1. Environment variables
        2. AWS profile
        3. IAM role (if running on AWS)

        Args:
            profile_name: AWS profile name to use if environment vars not found

        Example:
            provider = DefaultCredentialProvider()
            creds = await provider.get_credentials()
        """
        self.profile_name = profile_name

    async def get_credentials(self) -> Optional[AWSCredentials]:
        """
        Get credentials from multiple sources.

        Tries in order:
        1. Environment variables
        2. AWS profile

        Returns:
            AWSCredentials or None if no credentials found

        Example:
            provider = DefaultCredentialProvider(profile_name="production")
            creds = await provider.get_credentials()
            if creds:
                print("Credentials found!")
        """
        # Try environment variables first
        env_provider = EnvironmentCredentialProvider()
        creds = await env_provider.get_credentials()
        if creds:
            return creds

        # Try AWS profile
        profile_provider = ProfileCredentialProvider(self.profile_name)
        creds = await profile_provider.get_credentials()
        if creds:
            return creds

        # In production, also try IAM role credentials
        # This would use boto3 or aioboto3 to fetch instance metadata

        return None
