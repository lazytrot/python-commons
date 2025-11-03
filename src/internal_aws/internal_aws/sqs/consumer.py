"""
SQS consumer for long-polling message processing.

Provides a long-running consumer that continuously polls for messages.
"""

import asyncio
import logging
from typing import Optional, Callable, Any, Type, TypeVar, List

from pydantic import BaseModel

from .client import SQSClient, SQSConfig, SQSMessage, SQSProcessMessageResult
from ..auth.credentials import CredentialProvider


T = TypeVar('T', bound=BaseModel)

logger = logging.getLogger(__name__)


class SQSConsumer:
    """
    Long-polling SQS consumer.

    Continuously polls SQS queue for messages and processes them with a handler function.
    Supports graceful shutdown and automatic message deletion.

    Example:
        from internal_aws import SQSConsumer

        async def process_message(message):
            body = json.loads(message["Body"])
            print(f"Processing: {body}")
            # Do work...

        consumer = SQSConsumer(
            queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
            region="us-east-1",
            handler=process_message,
            max_messages=10,
            wait_time=20
        )

        # Start consuming
        await consumer.start()

        # Later, to stop:
        await consumer.stop()
    """

    def __init__(
        self,
        queue_url: str,
        region: str,
        handler: Callable[[SQSMessage], Any],
        max_messages: int = 10,
        wait_time: int = 20,
        visibility_timeout: int = 30,
        endpoint_url: Optional[str] = None,
        credential_provider: Optional[CredentialProvider] = None,
        polling_interval: float = 0.1,
        model_class: Optional[Type[T]] = None,
        auto_delete: bool = True
    ):
        """
        Initialize SQS consumer.

        Args:
            queue_url: SQS queue URL
            region: AWS region
            handler: Message handler function (sync or async)
            max_messages: Maximum messages per batch (1-10)
            wait_time: Long polling wait time in seconds (0-20)
            visibility_timeout: Visibility timeout for messages
            endpoint_url: Custom endpoint URL (for LocalStack)
            credential_provider: Optional credential provider
            polling_interval: Interval between polling cycles
            model_class: Optional Pydantic model class for deserialization
            auto_delete: Automatically delete successfully processed messages

        Example:
            async def handle_task(message):
                task = json.loads(message["Body"])
                print(f"Task: {task}")

            consumer = SQSConsumer(
                queue_url="https://...",
                region="us-east-1",
                handler=handle_task,
                max_messages=10,
                wait_time=20,
                auto_delete=True
            )
        """
        self.handler = handler
        self.max_messages = max_messages
        self.wait_time = wait_time
        self.visibility_timeout = visibility_timeout
        self.polling_interval = polling_interval
        self.model_class = model_class
        self.auto_delete = auto_delete

        # Create SQS client
        config = SQSConfig(
            queue_url=queue_url,
            region=region,
            endpoint_url=endpoint_url
        )
        self.client = SQSClient(config, credential_provider)

        # Consumer state
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """
        Start the consumer.

        Begins long-polling for messages and processing them with the handler.

        Example:
            consumer = SQSConsumer(...)
            await consumer.start()  # Runs until stop() is called
        """
        if self._running:
            logger.warning("Consumer already running")
            return

        self._running = True
        logger.info(
            f"Starting SQS consumer for queue: {self.client.config.queue_url}"
        )

        self._task = asyncio.create_task(self._consume_loop())

        try:
            await self._task
        except asyncio.CancelledError:
            logger.info("Consumer task cancelled")

    async def stop(self) -> None:
        """
        Stop the consumer.

        Gracefully stops the consumer after processing current batch.

        Example:
            await consumer.stop()
        """
        if not self._running:
            logger.warning("Consumer not running")
            return

        logger.info("Stopping SQS consumer...")
        self._running = False

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

        logger.info("Consumer stopped")

    async def _consume_loop(self) -> None:
        """
        Main consumer loop.

        Continuously polls for messages and processes them.
        """
        while self._running:
            try:
                # Process a batch of messages
                results = await self.process_batch(self.max_messages)

                # Log results
                successful = sum(1 for r in results if r["success"])
                failed = sum(1 for r in results if not r["success"])

                if results:
                    logger.info(
                        f"Processed batch: {successful} successful, {failed} failed"
                    )

                # Brief pause between polling cycles
                await asyncio.sleep(self.polling_interval)

            except Exception as e:
                logger.error(f"Error in consumer loop: {e}", exc_info=True)
                # Wait before retrying on error
                await asyncio.sleep(5)

    async def process_batch(self, batch_size: int = 10) -> List[SQSProcessMessageResult]:
        """
        Process a batch of messages.

        Args:
            batch_size: Number of messages to process

        Returns:
            List of processing results

        Example:
            # Process a single batch manually
            results = await consumer.process_batch(10)
            for result in results:
                if result["success"]:
                    print(f"Processed: {result['message']['MessageId']}")
                else:
                    print(f"Failed: {result['error']}")
        """
        results = await self.client.process_messages(
            handler=self.handler,
            max_number_of_messages=batch_size,
            wait_time_seconds=self.wait_time,
            visibility_timeout=self.visibility_timeout,
            model_class=self.model_class,
            auto_delete=self.auto_delete
        )

        return results
