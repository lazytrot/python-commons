"""
Integration tests for DynamoTable with LocalStack.

Tests real DynamoDB operations - NO MOCKING.
"""

import pytest
from pydantic import BaseModel


class TestUser(BaseModel):
    """Test model for DynamoDB."""
    user_id: str
    name: str
    email: str
    age: int = 0


@pytest.mark.integration
@pytest.mark.localstack
@pytest.mark.asyncio
class TestDynamoTable:
    """Test DynamoTable with real LocalStack DynamoDB."""

    async def test_put_and_get_item(self, dynamodb_table):
        """Test putting and getting item."""
        # Put item
        user = TestUser(user_id="123", name="John Doe", email="john@example.com", age=30)
        await dynamodb_table.put_item(user)
        
        # Get item
        retrieved = await dynamodb_table.get_item({"user_id": "123"})
        assert retrieved is not None
        assert retrieved.user_id == "123"
        assert retrieved.name == "John Doe"
        assert retrieved.email == "john@example.com"

    async def test_put_dict_and_get_item(self, dynamodb_table):
        """Test putting dict and getting item."""
        # Put as dict
        item_dict = {"user_id": "456", "name": "Jane Doe", "email": "jane@example.com", "age": 25}
        await dynamodb_table.put_item(item_dict)
        
        # Get item
        retrieved = await dynamodb_table.get_item({"user_id": "456"})
        assert retrieved.user_id == "456"
        assert retrieved.name == "Jane Doe"

    async def test_get_nonexistent_item(self, dynamodb_table):
        """Test getting non-existent item returns None."""
        result = await dynamodb_table.get_item({"user_id": "nonexistent"})
        assert result is None

    async def test_delete_item(self, dynamodb_table):
        """Test deleting item."""
        # Put item
        user = TestUser(user_id="789", name="Delete Me", email="delete@example.com")
        await dynamodb_table.put_item(user)
        
        # Delete item
        await dynamodb_table.delete_item({"user_id": "789"})
        
        # Verify deleted
        result = await dynamodb_table.get_item({"user_id": "789"})
        assert result is None

    async def test_query_items(self, dynamodb_table):
        """Test querying items."""
        # Put multiple items
        for i in range(5):
            user = TestUser(
                user_id=f"user{i}",
                name=f"User {i}",
                email=f"user{i}@example.com",
                age=20 + i
            )
            await dynamodb_table.put_item(user)
        
        # Query by user_id
        results = await dynamodb_table.query(
            key_condition_expression="user_id = :id",
            expression_attribute_values={":id": "user0"}
        )
        
        assert len(results) >= 1
        assert results[0].user_id == "user0"

    async def test_scan_items(self, dynamodb_table):
        """Test scanning all items."""
        # Put multiple items
        for i in range(3):
            user = TestUser(
                user_id=f"scan{i}",
                name=f"Scan {i}",
                email=f"scan{i}@example.com"
            )
            await dynamodb_table.put_item(user)
        
        # Scan all
        results = await dynamodb_table.scan()
        
        # Should have at least the items we added
        assert len(results) >= 3

    async def test_scan_with_filter(self, dynamodb_table):
        """Test scanning with filter expression."""
        # Put items with different ages
        for i in range(5):
            user = TestUser(
                user_id=f"filter{i}",
                name=f"Filter {i}",
                email=f"filter{i}@example.com",
                age=20 + i * 5
            )
            await dynamodb_table.put_item(user)
        
        # Scan with filter for age > 25
        results = await dynamodb_table.scan(
            filter_expression="age > :min_age",
            expression_attribute_values={":min_age": 25}
        )
        
        # Should have items with age > 25
        for user in results:
            if user.user_id.startswith("filter"):
                assert user.age > 25

    async def test_update_item(self, dynamodb_table):
        """Test updating item."""
        # Put item
        user = TestUser(user_id="update1", name="Original", email="original@example.com")
        await dynamodb_table.put_item(user)
        
        # Update item
        await dynamodb_table.update_item(
            key={"user_id": "update1"},
            update_expression="SET #name = :name",
            expression_attribute_values={":name": "Updated"},
            expression_attribute_names={"#name": "name"}
        )
        
        # Verify update
        retrieved = await dynamodb_table.get_item({"user_id": "update1"})
        assert retrieved.name == "Updated"

    async def test_batch_write_items(self, dynamodb_table):
        """Test batch writing items."""
        # Prepare items
        items = [
            {"user_id": f"batch{i}", "name": f"Batch {i}", "email": f"batch{i}@example.com", "age": 20 + i}
            for i in range(10)
        ]
        
        # Batch write
        await dynamodb_table.batch_write_items_to_table(items)
        
        # Verify all written
        for i in range(10):
            result = await dynamodb_table.get_item({"user_id": f"batch{i}"})
            assert result is not None
            assert result.name == f"Batch {i}"

    async def test_batch_get_items(self, dynamodb_table):
        """Test batch getting items."""
        # Put multiple items
        for i in range(5):
            user = TestUser(
                user_id=f"batchget{i}",
                name=f"BatchGet {i}",
                email=f"batchget{i}@example.com"
            )
            await dynamodb_table.put_item(user)
        
        # Batch get
        keys = [{"user_id": f"batchget{i}"} for i in range(5)]
        results = await dynamodb_table.batch_get_items_from_table(keys)
        
        # Should get all items
        assert len(results) >= 5

    async def test_serialization_deserialization(self, dynamodb_table):
        """Test serialization and deserialization of different types."""
        # Test with various data types
        user = TestUser(
            user_id="serial1",
            name="Serialization Test",
            email="serial@example.com",
            age=42
        )
        
        await dynamodb_table.put_item(user)
        
        # Get and verify all fields are correct type
        retrieved = await dynamodb_table.get_item({"user_id": "serial1"})
        assert isinstance(retrieved.user_id, str)
        assert isinstance(retrieved.name, str)
        assert isinstance(retrieved.age, int)
