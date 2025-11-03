"""SQS module for internal_aws."""

from .client import SQSClient, SQSConfig
from .consumer import SQSConsumer

__all__ = ["SQSClient", "SQSConfig", "SQSConsumer"]
