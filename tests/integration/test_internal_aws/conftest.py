"""Fixtures for internal_aws integration tests."""

import pytest
import pytest_asyncio
from testcontainers.localstack import LocalStackContainer
from testcontainers.core.waiting_utils import wait_for_logs

from internal_aws import (
    S3Client, S3ClientConfig,
    DynamoTable, DynamoDBConfig,
    SQSClient, SQSConfig,
    ExplicitCredentialProvider
)


@pytest.fixture(scope="session")
def localstack_container():
    """Start LocalStack container for AWS services."""
    localstack = LocalStackContainer(image="localstack/localstack:latest")
    localstack.with_services("s3", "dynamodb", "sqs")
    localstack.start()

    # Wait for LocalStack to be ready
    wait_for_logs(localstack, "Ready", timeout=60)

    yield localstack

    localstack.stop()


@pytest.fixture
def aws_credentials(localstack_container):
    """Create AWS credentials for LocalStack."""
    return ExplicitCredentialProvider(
        access_key_id="test",
        secret_access_key="test",
        region="us-east-1"
    )


@pytest.fixture
def s3_config(localstack_container):
    """S3 client configuration for LocalStack."""
    return S3ClientConfig(
        bucket_name="test-bucket",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest.fixture
def dynamodb_config(localstack_container):
    """DynamoDB configuration for LocalStack."""
    return DynamoDBConfig(
        table_name="test-table",
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest.fixture
def sqs_config(localstack_container):
    """SQS configuration for LocalStack."""
    # Create queue first
    import boto3
    sqs = boto3.client(
        "sqs",
        endpoint_url=localstack_container.get_url(),
        region_name="us-east-1",
        aws_access_key_id="test",
        aws_secret_access_key="test"
    )
    response = sqs.create_queue(QueueName="test-queue")
    queue_url = response["QueueUrl"]
    
    return SQSConfig(
        queue_url=queue_url,
        region="us-east-1",
        endpoint_url=localstack_container.get_url()
    )


@pytest_asyncio.fixture
async def s3_client(s3_config, aws_credentials):
    """S3 client connected to LocalStack."""
    client = S3Client(s3_config, aws_credentials)
    
    # Create bucket
    async with client.get_client() as s3:
        try:
            await s3.create_bucket(Bucket=s3_config.bucket_name)
        except Exception:
            pass  # Bucket might already exist
    
    yield client


@pytest_asyncio.fixture
async def dynamodb_table(dynamodb_config, aws_credentials):
    """DynamoDB table connected to LocalStack."""
    from pydantic import BaseModel
    
    class TestItem(BaseModel):
        id: str
        name: str
    
    table = DynamoTable(
        dynamodb_config,
        TestItem,
        aws_credentials,
        key_schema=[{"AttributeName": "id", "KeyType": "HASH"}],
        attribute_definitions=[{"AttributeName": "id", "AttributeType": "S"}]
    )
    
    # Create table
    try:
        await table.create_table()
    except Exception:
        pass  # Table might already exist
    
    yield table


@pytest_asyncio.fixture
async def sqs_client(sqs_config, aws_credentials):
    """SQS client connected to LocalStack."""
    client = SQSClient(sqs_config, aws_credentials)
    yield client
