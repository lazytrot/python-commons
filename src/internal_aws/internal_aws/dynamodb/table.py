"""
DynamoDB table client.

Provides async DynamoDB table operations with type safety.
"""

from typing import Optional, Dict, Any, List, Union, Type, TypeVar, Generic
from contextlib import asynccontextmanager

from pydantic import BaseModel, Field

try:
    import aioboto3
except ImportError:
    raise ImportError(
        "aioboto3 is required for DynamoDB operations. "
        "Install it with: pip install aioboto3"
    )

from ..auth.credentials import CredentialProvider, DefaultCredentialProvider


T = TypeVar('T', bound=BaseModel)


class DynamoDBConfig(BaseModel):
    """DynamoDB configuration."""

    table_name: str = Field(description="DynamoDB table name")
    region: str = Field(default="us-east-1", description="AWS region")
    endpoint_url: Optional[str] = Field(
        default=None,
        description="Custom endpoint URL (for LocalStack, etc.)"
    )


class DynamoTable(Generic[T]):
    """
    Generic DynamoDB table client.

    Provides type-safe DynamoDB operations with automatic serialization/deserialization.

    Example:
        from pydantic import BaseModel
        from internal_aws import DynamoTable, DynamoDBConfig

        class User(BaseModel):
            user_id: str
            name: str
            email: str

        config = DynamoDBConfig(
            table_name="users",
            region="us-east-1"
        )

        table = DynamoTable(config, User)

        # Put item
        user = User(user_id="123", name="John", email="john@example.com")
        await table.put_item(user)

        # Get item
        user = await table.get_item({"user_id": "123"})

        # Query
        users = await table.query(
            key_condition_expression="user_id = :id",
            expression_attribute_values={":id": "123"}
        )

        # Scan
        all_users = await table.scan()
    """

    def __init__(
        self,
        config: DynamoDBConfig,
        model_class: Type[T],
        credential_provider: Optional[CredentialProvider] = None,
        key_schema: Optional[List[Dict[str, str]]] = None,
        attribute_definitions: Optional[List[Dict[str, str]]] = None,
        provisioned_throughput: Optional[Dict[str, int]] = None
    ):
        """
        Initialize DynamoDB table client.

        Args:
            config: DynamoDB configuration
            model_class: Pydantic model class for type safety
            credential_provider: Optional credential provider
            key_schema: Key schema for table creation
            attribute_definitions: Attribute definitions for table creation
            provisioned_throughput: Provisioned throughput for table creation

        Example:
            config = DynamoDBConfig(table_name="users", region="us-east-1")
            table = DynamoTable(
                config,
                User,
                key_schema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                attribute_definitions=[{"AttributeName": "user_id", "AttributeType": "S"}]
            )
        """
        self.config = config
        self.model_class = model_class
        self.credential_provider = credential_provider or DefaultCredentialProvider()
        self.key_schema = key_schema
        self.attribute_definitions = attribute_definitions
        self.provisioned_throughput = provisioned_throughput or {
            "ReadCapacityUnits": 5,
            "WriteCapacityUnits": 5
        }

    async def _get_credentials(self):
        """Get AWS credentials from provider."""
        return await self.credential_provider.get_credentials()

    async def _get_client_kwargs(self) -> Dict[str, Any]:
        """
        Get client kwargs including credentials.

        Returns:
            Dictionary of kwargs for aioboto3 client creation
        """
        kwargs: Dict[str, Any] = {
            "service_name": "dynamodb",
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
        Get DynamoDB client as async context manager.

        Yields:
            aioboto3 DynamoDB client

        Example:
            async with table.get_client() as dynamodb:
                response = await dynamodb.describe_table(TableName="users")
        """
        session = aioboto3.Session()
        kwargs = await self._get_client_kwargs()
        async with session.client(**kwargs) as dynamodb_client:
            yield dynamodb_client

    async def create_table(self) -> Dict[str, Any]:
        """
        Create DynamoDB table.

        Returns:
            CreateTable response

        Example:
            table = DynamoTable(
                config,
                User,
                key_schema=[{"AttributeName": "user_id", "KeyType": "HASH"}],
                attribute_definitions=[{"AttributeName": "user_id", "AttributeType": "S"}]
            )
            await table.create_table()
        """
        if not self.key_schema or not self.attribute_definitions:
            raise ValueError("key_schema and attribute_definitions required for table creation")

        async with self.get_client() as dynamodb:
            response = await dynamodb.create_table(
                TableName=self.config.table_name,
                KeySchema=self.key_schema,
                AttributeDefinitions=self.attribute_definitions,
                ProvisionedThroughput=self.provisioned_throughput
            )
            return response

    async def delete_table(self) -> Dict[str, Any]:
        """
        Delete DynamoDB table.

        Returns:
            DeleteTable response

        Example:
            await table.delete_table()
        """
        async with self.get_client() as dynamodb:
            response = await dynamodb.delete_table(
                TableName=self.config.table_name
            )
            return response

    async def put_item(self, item: Union[T, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Put item to table.

        Args:
            item: Pydantic model instance or dictionary

        Returns:
            PutItem response

        Example:
            user = User(user_id="123", name="John", email="john@example.com")
            await table.put_item(user)

            # Or with dict
            await table.put_item({"user_id": "123", "name": "John"})
        """
        if isinstance(item, BaseModel):
            item_dict = item.model_dump()
        else:
            item_dict = item

        # Serialize to DynamoDB format
        dynamodb_item = self._serialize_item(item_dict)

        async with self.get_client() as dynamodb:
            response = await dynamodb.put_item(
                TableName=self.config.table_name,
                Item=dynamodb_item
            )
            return response

    async def get_item(self, key: Dict[str, Any]) -> Optional[T]:
        """
        Get item from table.

        Args:
            key: Primary key dictionary

        Returns:
            Pydantic model instance or None if not found

        Example:
            user = await table.get_item({"user_id": "123"})
            if user:
                print(user.name)
        """
        dynamodb_key = self._serialize_item(key)

        async with self.get_client() as dynamodb:
            response = await dynamodb.get_item(
                TableName=self.config.table_name,
                Key=dynamodb_key
            )

            if "Item" not in response:
                return None

            # Deserialize from DynamoDB format
            item_dict = self._deserialize_item(response["Item"])
            return self.model_class.model_validate(item_dict)

    async def delete_item(self, key: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delete item from table.

        Args:
            key: Primary key dictionary

        Returns:
            DeleteItem response

        Example:
            await table.delete_item({"user_id": "123"})
        """
        dynamodb_key = self._serialize_item(key)

        async with self.get_client() as dynamodb:
            response = await dynamodb.delete_item(
                TableName=self.config.table_name,
                Key=dynamodb_key
            )
            return response

    async def query(
        self,
        key_condition_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        filter_expression: Optional[str] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None,
        scan_index_forward: bool = True
    ) -> List[T]:
        """
        Query table.

        Args:
            key_condition_expression: Key condition expression
            expression_attribute_values: Expression attribute values
            expression_attribute_names: Expression attribute names
            filter_expression: Filter expression
            index_name: Index name for query
            limit: Maximum items to return
            scan_index_forward: Sort order (True=ascending, False=descending)

        Returns:
            List of Pydantic model instances

        Example:
            users = await table.query(
                key_condition_expression="user_id = :id",
                expression_attribute_values={":id": "123"}
            )

            # With filter
            active_users = await table.query(
                key_condition_expression="user_id = :id",
                expression_attribute_values={":id": "123", ":status": "active"},
                filter_expression="status = :status"
            )
        """
        # Serialize expression attribute values
        serialized_values = {
            k: self._serialize_value(v)
            for k, v in expression_attribute_values.items()
        }

        async with self.get_client() as dynamodb:
            kwargs = {
                "TableName": self.config.table_name,
                "KeyConditionExpression": key_condition_expression,
                "ExpressionAttributeValues": serialized_values,
                "ScanIndexForward": scan_index_forward
            }

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if index_name:
                kwargs["IndexName"] = index_name
            if limit:
                kwargs["Limit"] = limit

            response = await dynamodb.query(**kwargs)

            items = []
            for dynamodb_item in response.get("Items", []):
                item_dict = self._deserialize_item(dynamodb_item)
                items.append(self.model_class.model_validate(item_dict))

            return items

    async def scan(
        self,
        filter_expression: Optional[str] = None,
        expression_attribute_values: Optional[Dict[str, Any]] = None,
        expression_attribute_names: Optional[Dict[str, str]] = None,
        index_name: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[T]:
        """
        Scan table.

        Args:
            filter_expression: Filter expression
            expression_attribute_values: Expression attribute values
            expression_attribute_names: Expression attribute names
            index_name: Index name for scan
            limit: Maximum items to return

        Returns:
            List of Pydantic model instances

        Example:
            # Scan all
            all_users = await table.scan()

            # Scan with filter
            active_users = await table.scan(
                filter_expression="status = :status",
                expression_attribute_values={":status": "active"}
            )
        """
        async with self.get_client() as dynamodb:
            kwargs = {"TableName": self.config.table_name}

            if filter_expression:
                kwargs["FilterExpression"] = filter_expression
            if expression_attribute_values:
                kwargs["ExpressionAttributeValues"] = {
                    k: self._serialize_value(v)
                    for k, v in expression_attribute_values.items()
                }
            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if index_name:
                kwargs["IndexName"] = index_name
            if limit:
                kwargs["Limit"] = limit

            response = await dynamodb.scan(**kwargs)

            items = []
            for dynamodb_item in response.get("Items", []):
                item_dict = self._deserialize_item(dynamodb_item)
                items.append(self.model_class.model_validate(item_dict))

            return items

    async def update_item(
        self,
        key: Dict[str, Any],
        update_expression: str,
        expression_attribute_values: Dict[str, Any],
        expression_attribute_names: Optional[Dict[str, str]] = None,
        condition_expression: Optional[str] = None,
        return_values: str = "UPDATED_NEW"
    ) -> Dict[str, Any]:
        """
        Update item in table.

        Args:
            key: Primary key dictionary
            update_expression: Update expression
            expression_attribute_values: Expression attribute values
            expression_attribute_names: Expression attribute names
            condition_expression: Condition expression
            return_values: Return values option

        Returns:
            UpdateItem response

        Example:
            await table.update_item(
                key={"user_id": "123"},
                update_expression="SET #name = :name, #email = :email",
                expression_attribute_values={":name": "Jane", ":email": "jane@example.com"},
                expression_attribute_names={"#name": "name", "#email": "email"}
            )
        """
        dynamodb_key = self._serialize_item(key)
        serialized_values = {
            k: self._serialize_value(v)
            for k, v in expression_attribute_values.items()
        }

        async with self.get_client() as dynamodb:
            kwargs = {
                "TableName": self.config.table_name,
                "Key": dynamodb_key,
                "UpdateExpression": update_expression,
                "ExpressionAttributeValues": serialized_values,
                "ReturnValues": return_values
            }

            if expression_attribute_names:
                kwargs["ExpressionAttributeNames"] = expression_attribute_names
            if condition_expression:
                kwargs["ConditionExpression"] = condition_expression

            response = await dynamodb.update_item(**kwargs)
            return response

    async def batch_get_items(
        self,
        keys: List[Dict[str, Any]],
        consistent_read: bool = False,
        projection_expression: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch get items from table.

        Args:
            keys: List of primary key dictionaries
            consistent_read: Use consistent read
            projection_expression: Projection expression

        Returns:
            BatchGetItem response

        Example:
            response = await table.batch_get_items([
                {"user_id": "123"},
                {"user_id": "456"}
            ])
        """
        dynamodb_keys = [self._serialize_item(key) for key in keys]

        async with self.get_client() as dynamodb:
            request_items = {
                self.config.table_name: {
                    "Keys": dynamodb_keys,
                    "ConsistentRead": consistent_read
                }
            }
            if projection_expression:
                request_items[self.config.table_name]["ProjectionExpression"] = projection_expression

            response = await dynamodb.batch_get_item(RequestItems=request_items)
            return response

    async def batch_write_items(
        self,
        items_to_put: Optional[List[Dict[str, Any]]] = None,
        items_to_delete: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """
        Batch write items to table.

        Args:
            items_to_put: Items to put (full item dictionaries)
            items_to_delete: Items to delete (key dictionaries)

        Returns:
            BatchWriteItem response

        Example:
            await table.batch_write_items(
                items_to_put=[
                    {"user_id": "123", "name": "John"},
                    {"user_id": "456", "name": "Jane"}
                ],
                items_to_delete=[{"user_id": "789"}]
            )
        """
        request_items = []

        if items_to_put:
            for item in items_to_put:
                dynamodb_item = self._serialize_item(item)
                request_items.append({"PutRequest": {"Item": dynamodb_item}})

        if items_to_delete:
            for key in items_to_delete:
                dynamodb_key = self._serialize_item(key)
                request_items.append({"DeleteRequest": {"Key": dynamodb_key}})

        async with self.get_client() as dynamodb:
            response = await dynamodb.batch_write_item(
                RequestItems={self.config.table_name: request_items}
            )
            return response

    async def batch_write_items_to_table(
        self,
        items: List[Union[T, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """
        Batch write items to table (put only).

        Args:
            items: List of Pydantic model instances or dictionaries

        Returns:
            BatchWriteItem response

        Example:
            users = [
                User(user_id="123", name="John", email="john@example.com"),
                User(user_id="456", name="Jane", email="jane@example.com")
            ]
            await table.batch_write_items_to_table(users)
        """
        items_dicts = []
        for item in items:
            if isinstance(item, BaseModel):
                items_dicts.append(item.model_dump())
            else:
                items_dicts.append(item)

        return await self.batch_write_items(items_to_put=items_dicts)

    async def batch_get_items_from_table(
        self,
        keys: List[Dict[str, Any]],
        consistent_read: bool = False
    ) -> List[T]:
        """
        Batch get items from table with type safety.

        Args:
            keys: List of primary key dictionaries
            consistent_read: Use consistent read

        Returns:
            List of Pydantic model instances

        Example:
            users = await table.batch_get_items_from_table([
                {"user_id": "123"},
                {"user_id": "456"}
            ])
        """
        response = await self.batch_get_items(keys, consistent_read)

        items = []
        for dynamodb_item in response.get("Responses", {}).get(self.config.table_name, []):
            item_dict = self._deserialize_item(dynamodb_item)
            items.append(self.model_class.model_validate(item_dict))

        return items

    def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize item to DynamoDB format.

        Args:
            item: Item dictionary

        Returns:
            DynamoDB formatted item
        """
        return {k: self._serialize_value(v) for k, v in item.items()}

    def _serialize_value(self, value: Any) -> Dict[str, Any]:
        """
        Serialize value to DynamoDB format.

        Args:
            value: Python value

        Returns:
            DynamoDB formatted value
        """
        if isinstance(value, str):
            return {"S": value}
        elif isinstance(value, (int, float)):
            return {"N": str(value)}
        elif isinstance(value, bool):
            return {"BOOL": value}
        elif isinstance(value, bytes):
            return {"B": value}
        elif isinstance(value, list):
            return {"L": [self._serialize_value(v) for v in value]}
        elif isinstance(value, dict):
            return {"M": self._serialize_item(value)}
        elif value is None:
            return {"NULL": True}
        else:
            # Default to string
            return {"S": str(value)}

    def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deserialize item from DynamoDB format.

        Args:
            item: DynamoDB formatted item

        Returns:
            Python dictionary
        """
        return {k: self._deserialize_value(v) for k, v in item.items()}

    def _deserialize_value(self, value: Dict[str, Any]) -> Any:
        """
        Deserialize value from DynamoDB format.

        Args:
            value: DynamoDB formatted value

        Returns:
            Python value
        """
        if "S" in value:
            return value["S"]
        elif "N" in value:
            num_str = value["N"]
            return int(num_str) if "." not in num_str else float(num_str)
        elif "BOOL" in value:
            return value["BOOL"]
        elif "B" in value:
            return value["B"]
        elif "L" in value:
            return [self._deserialize_value(v) for v in value["L"]]
        elif "M" in value:
            return self._deserialize_item(value["M"])
        elif "NULL" in value:
            return None
        else:
            return None
