"""
internal_aws - AWS service integrations package.

Provides async clients for S3, DynamoDB, and SQS with credential management.
"""

from .auth.credentials import (
    AWSCredentials,
    CredentialProvider,
    ExplicitCredentialProvider,
    EnvironmentCredentialProvider,
    ProfileCredentialProvider,
    DefaultCredentialProvider,
)
from .s3 import S3Client, S3ClientConfig
from .dynamodb import DynamoTable, DynamoDBConfig
from .sqs import SQSClient, SQSConfig, SQSConsumer

__all__ = [
    # Auth
    "AWSCredentials",
    "CredentialProvider",
    "ExplicitCredentialProvider",
    "EnvironmentCredentialProvider",
    "ProfileCredentialProvider",
    "DefaultCredentialProvider",
    # S3
    "S3Client",
    "S3ClientConfig",
    # DynamoDB
    "DynamoTable",
    "DynamoDBConfig",
    # SQS
    "SQSClient",
    "SQSConfig",
    "SQSConsumer",
]
