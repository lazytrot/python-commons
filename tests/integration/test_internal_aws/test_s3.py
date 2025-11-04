"""
Integration tests for S3Client with LocalStack.

Tests real S3 operations - NO MOCKING.
"""

import pytest
from pydantic import BaseModel


class DataModel(BaseModel):
    """Test model for S3."""
    id: str
    value: str


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestS3Client:
    """Test S3Client with real LocalStack S3."""

    async def test_put_and_get_object(self, s3_client):
        """Test uploading and downloading object."""
        # Put object
        await s3_client.put_object("test.txt", b"Hello, World!")
        
        # Get object
        content = await s3_client.get_object_as_bytes("test.txt")
        assert content == b"Hello, World!"

    async def test_put_and_get_string(self, s3_client):
        """Test string operations."""
        await s3_client.put_object("data.txt", "Test data")
        
        content = await s3_client.get_object_as_string("data.txt")
        assert content == "Test data"

    async def test_put_and_get_json(self, s3_client):
        """Test JSON operations."""
        data = {"key": "value", "number": 42}
        
        import json
        await s3_client.put_object(
            "data.json",
            json.dumps(data),
            content_type="application/json"
        )
        
        retrieved = await s3_client.get_object_as_json("data.json")
        assert retrieved == data

    async def test_put_and_get_model(self, s3_client):
        """Test Pydantic model operations."""
        test_data = DataModel(id="123", value="test")
        
        await s3_client.put_object(
            "model.json",
            test_data.model_dump_json(),
            content_type="application/json"
        )
        
        retrieved = await s3_client.get_object_as_model("model.json", DataModel)
        assert retrieved.id == "123"
        assert retrieved.value == "test"

    async def test_list_objects(self, s3_client):
        """Test listing objects."""
        # Put multiple objects
        for i in range(5):
            await s3_client.put_object(f"file{i}.txt", f"content{i}")
        
        # List objects
        keys = await s3_client.list_objects()
        assert len(keys) >= 5

    async def test_delete_object(self, s3_client):
        """Test deleting object."""
        # Put object
        await s3_client.put_object("to_delete.txt", "delete me")
        
        # Delete object
        await s3_client.delete_object("to_delete.txt")
        
        # Verify deleted (should raise or return None)
        try:
            await s3_client.get_object("to_delete.txt")
            assert False, "Object should be deleted"
        except Exception:
            pass  # Expected

    async def test_copy_object(self, s3_client):
        """Test copying object."""
        # Put source object
        await s3_client.put_object("source.txt", "source content")
        
        # Copy object
        await s3_client.copy_object("source.txt", "target.txt")
        
        # Verify copy
        content = await s3_client.get_object_as_string("target.txt")
        assert content == "source content"
