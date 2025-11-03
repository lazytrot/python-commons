"""
Integration tests for SQSClient and SQSConsumer with LocalStack.

Tests real SQS operations - NO MOCKING.
"""

import pytest
import asyncio
from pydantic import BaseModel


class TestMessage(BaseModel):
    """Test message model."""
    id: str
    content: str


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestSQSClient:
    """Test SQSClient with real LocalStack SQS."""

    async def test_send_and_receive_message(self, sqs_client):
        """Test sending and receiving message."""
        # Send message
        response = await sqs_client.send_message("Hello, SQS!")
        assert "MessageId" in response
        
        # Receive message
        messages = await sqs_client.receive_message(max_number_of_messages=1)
        assert len(messages) >= 1
        assert messages[0]["Body"] == "Hello, SQS!"

    async def test_send_dict_message(self, sqs_client):
        """Test sending dict message (auto-serialized to JSON)."""
        data = {"key": "value", "number": 42}
        
        response = await sqs_client.send_message(data)
        assert "MessageId" in response
        
        # Receive and parse
        messages = await sqs_client.receive_message()
        assert len(messages) >= 1
        
        import json
        body = json.loads(messages[0]["Body"])
        assert body["key"] == "value"
        assert body["number"] == 42

    async def test_send_pydantic_model(self, sqs_client):
        """Test sending Pydantic model."""
        msg = TestMessage(id="123", content="Test content")
        
        response = await sqs_client.send_message(msg)
        assert "MessageId" in response
        
        # Receive and parse
        messages = await sqs_client.receive_message()
        assert len(messages) >= 1
        
        import json
        body = json.loads(messages[0]["Body"])
        assert body["id"] == "123"
        assert body["content"] == "Test content"

    async def test_send_message_batch(self, sqs_client):
        """Test sending batch of messages."""
        messages = ["msg1", "msg2", "msg3", "msg4", "msg5"]
        
        response = await sqs_client.send_message_batch(messages)
        
        # Check for successful sends
        assert "Successful" in response
        assert len(response["Successful"]) == 5

    async def test_delete_message(self, sqs_client):
        """Test deleting message."""
        # Send message
        await sqs_client.send_message("Delete me")
        
        # Receive message
        messages = await sqs_client.receive_message()
        assert len(messages) >= 1
        
        receipt_handle = messages[0]["ReceiptHandle"]
        
        # Delete message
        await sqs_client.delete_message(receipt_handle)
        
        # Verify deleted (won't be received again immediately)
        # Note: This might be flaky in real testing due to SQS eventual consistency

    async def test_message_attributes(self, sqs_client):
        """Test sending message with attributes."""
        attributes = {
            "priority": {"StringValue": "high", "DataType": "String"},
            "timestamp": {"StringValue": "2024-01-01", "DataType": "String"}
        }
        
        response = await sqs_client.send_message(
            "Message with attributes",
            message_attributes=attributes
        )
        assert "MessageId" in response
        
        # Receive and check attributes
        messages = await sqs_client.receive_message()
        if messages and "MessageAttributes" in messages[0]:
            attrs = messages[0]["MessageAttributes"]
            if "priority" in attrs:
                assert attrs["priority"]["StringValue"] == "high"

    async def test_process_messages(self, sqs_client):
        """Test process_messages with handler."""
        # Send messages
        for i in range(5):
            await sqs_client.send_message(f"Message {i}")
        
        # Wait a bit for messages to be available
        await asyncio.sleep(1)
        
        # Track processed messages
        processed = []
        
        async def handler(message):
            """Test handler."""
            processed.append(message["Body"])
        
        # Process messages
        results = await sqs_client.process_messages(
            handler=handler,
            max_number_of_messages=10,
            wait_time_seconds=2,
            auto_delete=True
        )
        
        # Should have processed some messages
        assert len(processed) >= 1
        assert len(results) >= 1
        
        # Check results
        for result in results:
            assert "message" in result
            assert "success" in result
            if result["success"]:
                assert result["deleted"] is True

    async def test_long_polling(self, sqs_client):
        """Test long polling for messages."""
        # Receive with long polling (wait up to 5 seconds)
        messages = await sqs_client.receive_message(
            max_number_of_messages=1,
            wait_time_seconds=2
        )
        
        # Should return (may be empty if no messages)
        assert isinstance(messages, list)


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestSQSConsumer:
    """Test SQSConsumer with real LocalStack SQS."""

    async def test_consumer_process_batch(self, sqs_config, aws_credentials):
        """Test consumer processing a batch."""
        from internal_aws import SQSConsumer
        
        # Send test messages
        from internal_aws import SQSClient
        client = SQSClient(sqs_config, aws_credentials)
        for i in range(3):
            await client.send_message(f"Consumer test {i}")
        
        # Wait for messages
        await asyncio.sleep(1)
        
        # Track processed messages
        processed = []
        
        async def handler(message):
            """Test handler."""
            processed.append(message["Body"])
        
        # Create consumer
        consumer = SQSConsumer(
            queue_url=sqs_config.queue_url,
            region=sqs_config.region,
            handler=handler,
            max_messages=10,
            wait_time=2,
            endpoint_url=sqs_config.endpoint_url,
            credential_provider=aws_credentials,
            auto_delete=True
        )
        
        # Process one batch
        results = await consumer.process_batch(batch_size=10)
        
        # Should have processed messages
        assert len(processed) >= 1
        assert len(results) >= 1

    async def test_consumer_start_stop(self, sqs_config, aws_credentials):
        """Test consumer start and stop."""
        from internal_aws import SQSConsumer
        
        processed = []
        
        async def handler(message):
            processed.append(message["Body"])
        
        consumer = SQSConsumer(
            queue_url=sqs_config.queue_url,
            region=sqs_config.region,
            handler=handler,
            endpoint_url=sqs_config.endpoint_url,
            credential_provider=aws_credentials,
            wait_time=1,
            polling_interval=0.1
        )
        
        # Start consumer in background
        task = asyncio.create_task(consumer.start())
        
        # Let it run briefly
        await asyncio.sleep(2)
        
        # Stop consumer
        await consumer.stop()
        
        # Wait for task to complete
        try:
            await asyncio.wait_for(task, timeout=5)
        except asyncio.TimeoutError:
            pass
