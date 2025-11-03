"""
SQS client for queue operations.

Provides async SQS operations with aioboto3.
"""

import json
from typing import Optional, Dict, Any, List, Union, Type, TypeVar, Callable, Awaitable
from typing_extensions import TypedDict
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

try:
    import aioboto3
except ImportError:
    raise ImportError(
        "aioboto3 is required for SQS operations. "
        "Install it with: pip install aioboto3"
    )

from ..auth.credentials import CredentialProvider, DefaultCredentialProvider


T = TypeVar('T', bound=BaseModel)


# TypedDict definitions for SQS responses
class SQSResponseMetadata(TypedDict, total=False):
    """SQS response metadata."""
    RequestId: str
    HTTPStatusCode: int
    HTTPHeaders: Dict[str, str]


class SQSSendMessageResponse(TypedDict):
    """SQS SendMessage response."""
    MessageId: str
    MD5OfMessageBody: str
    MD5OfMessageAttributes: str
    ResponseMetadata: SQSResponseMetadata


class SQSBatchResultErrorEntry(TypedDict):
    """SQS batch result error entry."""
    Id: str
    SenderFault: bool
    Code: str
    Message: str


class SQSBatchResultSuccessEntry(TypedDict):
    """SQS batch result success entry."""
    Id: str
    MessageId: str
    MD5OfMessageBody: str


class SQSSendMessageBatchResponse(TypedDict):
    """SQS SendMessageBatch response."""
    Successful: List[SQSBatchResultSuccessEntry]
    Failed: List[SQSBatchResultErrorEntry]
    ResponseMetadata: SQSResponseMetadata


class SQSDeleteMessageResponse(TypedDict):
    """SQS DeleteMessage response."""
    ResponseMetadata: SQSResponseMetadata


class SQSDeleteMessageBatchResponse(TypedDict):
    """SQS DeleteMessageBatch response."""
    Successful: List[Dict[str, str]]
    Failed: List[SQSBatchResultErrorEntry]
    ResponseMetadata: SQSResponseMetadata


class SQSPurgeQueueResponse(TypedDict):
    """SQS PurgeQueue response."""
    ResponseMetadata: SQSResponseMetadata


class SQSMessageAttributes(TypedDict, total=False):
    """SQS message attributes."""
    StringValue: str
    BinaryValue: bytes
    DataType: str


class SQSMessage(TypedDict, total=False):
    """SQS message."""
    MessageId: str
    ReceiptHandle: str
    Body: str
    Attributes: Dict[str, str]
    MessageAttributes: Dict[str, SQSMessageAttributes]
    MD5OfBody: str


class SQSProcessMessageResult(TypedDict):
    """Result of processing an SQS message."""
    message: SQSMessage
    success: bool
    error: Optional[str]
    deleted: bool


class SQSConfig(BaseModel):
    """SQS configuration."""

    queue_url: str = Field(description="SQS queue URL")
    region: str = Field(default="us-east-1", description="AWS region")
    endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL (for LocalStack, etc.)"
    )


class SQSClient:
    """
    SQS client for queue operations.

    Provides async methods for SQS operations including send, receive, delete, etc.

    Example:
        from internal_aws import SQSClient, SQSConfig

        config = SQSConfig(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
            region="us-east-1"
        )

        client = SQSClient(config)

        # Send message
        await client.send_message("Hello, World!")

        # Send with attributes
        await client.send_message(
            {"data": "value"},
            message_attributes={"priority": {"StringValue": "high", "DataType": "String"}}
        )

        # Receive messages
        messages = await client.receive_message(max_number_of_messages=10)

        # Process and delete
        for msg in messages:
            print(msg["Body"])
            await client.delete_message(msg["ReceiptHandle"])
    """

    def __init__(
        self,
        config: SQSConfig,
        credential_provider: Optional[CredentialProvider] = None
    ):
        """
        Initialize SQS client.

        Args:
            config: SQS client configuration
            credential_provider: Optional credential provider

        Example:
            config = SQSConfig(queue_url="https://...", region="us-east-1")
            client = SQSClient(config)
        """
        self.config = config
        self.credential_provider = credential_provider or DefaultCredentialProvider()

    async def _get_credentials(self) -> Optional[Any]:
        """Get AWS credentials from provider."""
        return await self.credential_provider.get_credentials()

    async def _get_client_kwargs(self) -> Dict[str, Any]:
        """
        Get client kwargs including credentials.

        Returns:
            Dictionary of kwargs for aioboto3 client creation
        """
        kwargs: Dict[str, Any] = {
            "service_name": "sqs",
            "region_name": self.config.region,
        }

        if self.config.endpoint_url:
            kwargs["endpoint_url"] = self.config.endpoint_url

        creds = await self._get_credentials()
        if creds:
            creds_dict = creds.to_dict()
            kwargs.update(creds_dict)

        return kwargs

    @asynccontextmanager
    async def get_client(self):
        """
        Get SQS client as async context manager.

        Yields:
            aioboto3 SQS client

        Example:
            async with client.get_client() as sqs:
                response = await sqs.get_queue_attributes(
                    QueueUrl=client.config.queue_url,
                    AttributeNames=["All"]
                )
        """
        session = aioboto3.Session()
        kwargs = await self._get_client_kwargs()
        async with session.client(**kwargs) as sqs_client:
            yield sqs_client

    async def create_queue(
        self,
        queue_name: str,
        attributes: Optional[Dict[str, str]] = None
    ) -> str:
        """
        Create SQS queue.

        Args:
            queue_name: Queue name
            attributes: Queue attributes

        Returns:
            Queue URL

        Example:
            queue_url = await client.create_queue(
                "my-queue",
                attributes={
                    "VisibilityTimeout": "30",
                    "MessageRetentionPeriod": "86400"
                }
            )
        """
        async with self.get_client() as sqs:
            response = await sqs.create_queue(
                QueueName=queue_name,
                Attributes=attributes or {}
            )
            return response["QueueUrl"]

    async def send_message(
        self,
        message: Union[str, Dict[str, Any], BaseModel],
        message_attributes: Optional[Dict[str, Dict[str, str]]] = None,
        delay_seconds: Optional[int] = None
    ) -> SQSSendMessageResponse:
        """
        Send message to queue.

        Args:
            message: Message body (string, dict, or Pydantic model)
            message_attributes: Message attributes
            delay_seconds: Delay in seconds

        Returns:
            SendMessage response

        Example:
            # Send string
            await client.send_message("Hello")

            # Send dict (auto-serialized to JSON)
            await client.send_message({"key": "value"})

            # Send Pydantic model
            from pydantic import BaseModel
            class Task(BaseModel):
                task_id: str
                name: str

            task = Task(task_id="123", name="Process data")
            await client.send_message(task)

            # With attributes
            await client.send_message(
                "Hello",
                message_attributes={
                    "priority": {"StringValue": "high", "DataType": "String"}
                }
            )
        """
        # Convert message to string
        if isinstance(message, BaseModel):
            message_body = message.model_dump_json()
        elif isinstance(message, dict):
            message_body = json.dumps(message)
        else:
            message_body = str(message)

        async with self.get_client() as sqs:
            kwargs = {
                "QueueUrl": self.config.queue_url,
                "MessageBody": message_body
            }

            if message_attributes:
                kwargs["MessageAttributes"] = message_attributes
            if delay_seconds is not None:
                kwargs["DelaySeconds"] = delay_seconds

            response = await sqs.send_message(**kwargs)
            return response

    async def send_message_batch(
        self,
        messages: List[Union[str, Dict[str, Any], BaseModel]],
        message_attributes: Optional[List[Dict[str, Dict[str, str]]]] = None,
        delay_seconds: Optional[int] = None
    ) -> SQSSendMessageBatchResponse:
        """
        Send batch of messages to queue.

        Args:
            messages: List of messages
            message_attributes: List of message attributes (parallel to messages)
            delay_seconds: Delay in seconds

        Returns:
            SendMessageBatch response

        Example:
            messages = ["msg1", "msg2", "msg3"]
            response = await client.send_message_batch(messages)
            print(f"Successful: {len(response['Successful'])}")
            print(f"Failed: {len(response['Failed'])}")
        """
        entries = []
        for i, message in enumerate(messages):
            # Convert message to string
            if isinstance(message, BaseModel):
                message_body = message.model_dump_json()
            elif isinstance(message, dict):
                message_body = json.dumps(message)
            else:
                message_body = str(message)

            entry = {
                "Id": str(i),
                "MessageBody": message_body
            }

            if message_attributes and i < len(message_attributes):
                entry["MessageAttributes"] = message_attributes[i]
            if delay_seconds is not None:
                entry["DelaySeconds"] = delay_seconds

            entries.append(entry)

        async with self.get_client() as sqs:
            response = await sqs.send_message_batch(
                QueueUrl=self.config.queue_url,
                Entries=entries
            )
            return response

    async def receive_message(
        self,
        max_number_of_messages: int = 1,
        wait_time_seconds: Optional[int] = None,
        visibility_timeout: Optional[int] = None,
        model_class: Optional[Type[T]] = None
    ) -> List[SQSMessage]:
        """
        Receive messages from queue.

        Args:
            max_number_of_messages: Maximum messages to receive (1-10)
            wait_time_seconds: Long polling wait time
            visibility_timeout: Visibility timeout for received messages
            model_class: Optional Pydantic model class for deserialization

        Returns:
            List of messages

        Example:
            # Simple receive
            messages = await client.receive_message(max_number_of_messages=10)

            # Long polling (wait up to 20 seconds)
            messages = await client.receive_message(
                max_number_of_messages=10,
                wait_time_seconds=20
            )

            # With Pydantic model
            from pydantic import BaseModel
            class Task(BaseModel):
                task_id: str
                name: str

            messages = await client.receive_message(
                max_number_of_messages=10,
                model_class=Task
            )
            for msg in messages:
                task = json.loads(msg["Body"])  # Or use model_class
        """
        async with self.get_client() as sqs:
            kwargs = {
                "QueueUrl": self.config.queue_url,
                "MaxNumberOfMessages": max_number_of_messages,
                "MessageAttributeNames": ["All"]
            }

            if wait_time_seconds is not None:
                kwargs["WaitTimeSeconds"] = wait_time_seconds
            if visibility_timeout is not None:
                kwargs["VisibilityTimeout"] = visibility_timeout

            response = await sqs.receive_message(**kwargs)
            messages = response.get("Messages", [])

            # If model_class provided, parse Body field
            if model_class and messages:
                for msg in messages:
                    try:
                        body_data = json.loads(msg["Body"])
                        msg["_parsed"] = model_class.model_validate(body_data)
                    except Exception:
                        pass  # Keep original if parsing fails

            return messages

    async def delete_message(self, receipt_handle: str) -> SQSDeleteMessageResponse:
        """
        Delete message from queue.

        Args:
            receipt_handle: Receipt handle from received message

        Returns:
            DeleteMessage response

        Example:
            messages = await client.receive_message()
            for msg in messages:
                # Process message
                print(msg["Body"])
                # Delete after processing
                await client.delete_message(msg["ReceiptHandle"])
        """
        async with self.get_client() as sqs:
            response = await sqs.delete_message(
                QueueUrl=self.config.queue_url,
                ReceiptHandle=receipt_handle
            )
            return response

    async def delete_message_batch(
        self,
        entries: List[Dict[str, str]]
    ) -> SQSDeleteMessageBatchResponse:
        """
        Delete batch of messages from queue.

        Args:
            entries: List of entries with Id and ReceiptHandle

        Returns:
            DeleteMessageBatch response

        Example:
            messages = await client.receive_message(max_number_of_messages=10)
            entries = [
                {"Id": str(i), "ReceiptHandle": msg["ReceiptHandle"]}
                for i, msg in enumerate(messages)
            ]
            await client.delete_message_batch(entries)
        """
        async with self.get_client() as sqs:
            response = await sqs.delete_message_batch(
                QueueUrl=self.config.queue_url,
                Entries=entries
            )
            return response

    async def purge_queue(self) -> SQSPurgeQueueResponse:
        """
        Purge all messages from queue.

        Returns:
            PurgeQueue response

        Example:
            await client.purge_queue()
        """
        async with self.get_client() as sqs:
            response = await sqs.purge_queue(QueueUrl=self.config.queue_url)
            return response

    async def process_messages(
        self,
        handler: Callable[[SQSMessage], Any],
        max_number_of_messages: int = 10,
        wait_time_seconds: Optional[int] = None,
        visibility_timeout: Optional[int] = None,
        model_class: Optional[Type[T]] = None,
        auto_delete: bool = True
    ) -> List[SQSProcessMessageResult]:
        """
        Receive and process messages with handler function.

        Args:
            handler: Message handler function (sync or async)
            max_number_of_messages: Maximum messages to receive
            wait_time_seconds: Long polling wait time
            visibility_timeout: Visibility timeout
            model_class: Optional Pydantic model class
            auto_delete: Automatically delete successfully processed messages

        Returns:
            List of processing results

        Example:
            async def process_task(message):
                body = json.loads(message["Body"])
                print(f"Processing: {body}")
                # Do work...

            results = await client.process_messages(
                handler=process_task,
                max_number_of_messages=10,
                wait_time_seconds=20,
                auto_delete=True
            )

            for result in results:
                if not result["success"]:
                    print(f"Failed: {result['error']}")
        """
        messages = await self.receive_message(
            max_number_of_messages=max_number_of_messages,
            wait_time_seconds=wait_time_seconds,
            visibility_timeout=visibility_timeout,
            model_class=model_class
        )

        results: List[SQSProcessMessageResult] = []

        for message in messages:
            result: SQSProcessMessageResult = {
                "message": message,
                "success": False,
                "error": None,
                "deleted": False
            }

            try:
                # Call handler (support both sync and async)
                if asyncio.iscoroutinefunction(handler):
                    await handler(message)
                else:
                    handler(message)

                result["success"] = True

                # Auto-delete if successful and enabled
                if auto_delete:
                    await self.delete_message(message["ReceiptHandle"])
                    result["deleted"] = True

            except Exception as e:
                result["error"] = str(e)

            results.append(result)

        return results


# Import asyncio for iscoroutinefunction
import asyncio
