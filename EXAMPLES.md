# Python Commons - Comprehensive Usage Examples

This document provides detailed examples for every feature in all packages.

---

## Table of Contents
1. [internal-base](#internal-base-examples)
2. [internal-http](#internal-http-examples)
3. [internal-rdbms](#internal-rdbms-examples)
4. [internal-aws](#internal-aws-examples)
5. [internal-fastapi](#internal-fastapi-examples)

---

# internal-base Examples

## Logging

### Example 1: Basic Text Logging
```python
from internal_base import LoggingConfig, LogFormat, configure_logging, getLogger

# Configure text logging with INFO level
config = LoggingConfig(
    format=LogFormat.TEXT,
    level="INFO"
)
configure_logging(config)

# Get logger and use it
logger = getLogger(__name__)
logger.info("Application started")
logger.debug("This won't show (level is INFO)")
logger.warning("Warning message")
logger.error("Error occurred")
```

**API Explanation:**
- `LoggingConfig`: Configuration model with `format` (TEXT/JSON) and `level` (DEBUG/INFO/WARNING/ERROR)
- `configure_logging()`: Sets up root logger with coloredlogs (TEXT) or JSON formatting
- `getLogger()`: Returns standard Python logger for the given name

### Example 2: JSON Logging for Production
```python
from internal_base import LoggingConfig, LogFormat, configure_logging, getLogger

# Configure JSON logging for production
config = LoggingConfig(
    format=LogFormat.JSON,
    level="WARNING",  # Only warnings and errors
    propagate=False
)
configure_logging(config)

logger = getLogger("myapp")

# All logs will be JSON formatted
logger.warning("Low disk space", extra={
    "disk_usage": "85%",
    "threshold": "80%"
})

# Output: {"timestamp": "...", "level": "WARNING", "message": "Low disk space", ...}
```

**API Explanation:**
- `LogFormat.JSON`: Outputs structured JSON logs (uses pythonjsonlogger)
- `extra` dict: Additional fields in JSON output
- Perfect for log aggregation systems (ELK, Datadog, etc.)

---

## Async Services

### Example 1: Creating a Background Service
```python
import asyncio
from internal_base import AsyncService, ServiceState

class DatabaseCleanupService(AsyncService):
    """Cleans up old database records periodically."""
    
    def __init__(self):
        super().__init__(name="DatabaseCleanup")
        self._task = None
    
    async def _start(self) -> None:
        """Start the cleanup loop."""
        self._task = asyncio.create_task(self._cleanup_loop())
    
    async def _stop(self) -> None:
        """Stop the cleanup loop."""
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
    
    async def _health_check(self) -> bool:
        """Check if service is healthy."""
        return self._task is not None and not self._task.done()
    
    async def _cleanup_loop(self):
        """Periodic cleanup loop."""
        while True:
            print("Cleaning up old records...")
            # Your cleanup logic here
            await asyncio.sleep(3600)  # Every hour

# Usage
async def main():
    service = DatabaseCleanupService()
    
    # Start service
    await service.start()
    print(f"Service state: {service.state}")  # RUNNING
    
    # Check health
    is_healthy = await service.is_healthy()
    print(f"Healthy: {is_healthy}")  # True
    
    # Stop service
    await service.stop()
    print(f"Service state: {service.state}")  # STOPPED

asyncio.run(main())
```

**API Explanation:**
- `AsyncService`: Abstract base class providing lifecycle management
- Must implement: `_start()`, `_stop()`, `_health_check()`
- Provides: `start()`, `stop()`, `is_healthy()`, `state` property
- `ServiceState`: Enum (IDLE, STARTING, RUNNING, STOPPING, STOPPED, FAILED)

### Example 2: Using Service as Context Manager
```python
from internal_base import AsyncService
import asyncio

class CacheWarmer(AsyncService):
    """Warms up cache on startup."""
    
    async def _start(self) -> None:
        print("Warming cache...")
        await asyncio.sleep(2)
        print("Cache warmed!")
    
    async def _stop(self) -> None:
        print("Flushing cache...")
        await asyncio.sleep(1)
    
    async def _health_check(self) -> bool:
        return True

# Use as context manager
async def main():
    async with CacheWarmer() as service:
        # Service is automatically started
        print("Service running, doing work...")
        await asyncio.sleep(5)
        # Service automatically stopped on exit
    
    print("Service stopped")

asyncio.run(main())
```

**API Explanation:**
- Context manager support via `__aenter__`/`__aexit__`
- Automatic start on enter, stop on exit
- Ensures proper cleanup even if exceptions occur

---

# internal-http Examples

## HTTP Client

### Example 1: Simple GET Request
```python
import asyncio
from internal_http import HttpClient

async def main():
    client = HttpClient(base_url="https://api.github.com")
    
    async with client:
        # GET request
        response = await client.get("/users/octocat")
        data = response.json()
        print(f"User: {data['login']}, Repos: {data['public_repos']}")

asyncio.run(main())
```

**API Explanation:**
- `HttpClient(base_url)`: Creates client with base URL
- `get(url)`: Async GET request, returns httpx.Response
- Context manager ensures proper cleanup

### Example 2: POST with Retry and Authentication
```python
import asyncio
from internal_http import HttpClient, RetryConfig, BearerAuth, AuthConfig

async def main():
    # Configure retry logic
    retry = RetryConfig(
        max_attempts=3,
        retry_statuses=[500, 502, 503],
        backoff_factor=1.0,
        jitter=True
    )
    
    # Configure authentication
    auth = BearerAuth("ghp_your_token_here")
    auth_config = AuthConfig(auth=auth)
    
    # Create client
    client = HttpClient(
        base_url="https://api.github.com",
        retries=retry,
        auth_config=auth_config
    )
    
    async with client:
        # POST request with retry and auth
        response = await client.post(
            "/repos/owner/repo/issues",
            json={
                "title": "Bug report",
                "body": "Description here"
            }
        )
        print(f"Created issue: {response.json()['number']}")

asyncio.run(main())
```

**API Explanation:**
- `RetryConfig`: Configures retry behavior
  - `max_attempts`: How many times to retry
  - `retry_statuses`: HTTP status codes to retry
  - `backoff_factor`: Exponential backoff multiplier
  - `jitter`: Add randomness to prevent thundering herd
- `BearerAuth(token)`: Bearer token authentication
- `AuthConfig`: Wraps auth for client
- Retries happen automatically on configured status codes

### Example 3: Pydantic Model Integration
```python
import asyncio
from pydantic import BaseModel
from internal_http import HttpClient

class User(BaseModel):
    login: str
    id: int
    public_repos: int
    followers: int

class CreateIssue(BaseModel):
    title: str
    body: str
    labels: list[str] = []

async def main():
    client = HttpClient(base_url="https://api.github.com")
    
    async with client:
        # GET and parse to Pydantic model
        user = await client.get_model("/users/octocat", User)
        print(f"User {user.login} has {user.public_repos} repos")
        
        # POST Pydantic model
        issue = CreateIssue(
            title="Feature request",
            body="Add dark mode",
            labels=["enhancement"]
        )
        response = await client.post_model(
            "/repos/owner/repo/issues",
            issue,
            response_model=dict  # Or another Pydantic model
        )
        print(f"Created: {response}")

asyncio.run(main())
```

**API Explanation:**
- `get_model(url, Model)`: GET request + parse response to Pydantic model
- `post_model(url, model, response_model)`: POST model + parse response
- Also available: `put_model()`, `patch_model()`, `delete_model()`
- Automatic JSON serialization/deserialization

### Example 4: Different Authentication Methods
```python
from internal_http import (
    HttpClient, BearerAuth, BasicAuth, ApiKeyAuth, AuthConfig
)

# Bearer token (OAuth, JWT)
bearer = BearerAuth("my-jwt-token")

# Basic auth (username/password)
basic = BasicAuth("username", "password")

# API key in header
api_key = ApiKeyAuth("sk-abc123", header_name="X-API-Key")

# API key with prefix
api_key_prefix = ApiKeyAuth(
    "secret-key",
    header_name="Authorization",
    prefix="ApiKey"
)

# Use any auth method
client = HttpClient(
    base_url="https://api.example.com",
    auth_config=AuthConfig(auth=bearer)  # or basic, api_key, etc.
)
```

**API Explanation:**
- `BearerAuth(token)`: Adds `Authorization: Bearer <token>`
- `BasicAuth(user, pass)`: Adds `Authorization: Basic <base64>`
- `ApiKeyAuth(key, header, prefix)`: Adds custom header with optional prefix
- All auth classes implement `auth_flow(request)` method

---

# internal-rdbms Examples

## Database Connections

### Example 1: PostgreSQL Connection
```python
import asyncio
from sqlalchemy import Column, Integer, String, select
from sqlalchemy.orm import DeclarativeBase
from internal_rdbms import PostgresDatabase, DatabaseConfig

# Define model
class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    name = Column(String(50))
    email = Column(String(100))

async def main():
    # Configure PostgreSQL
    config = DatabaseConfig(
        driver="postgresql+asyncpg",
        host="localhost",
        port=5432,
        user="myuser",
        password="mypass",
        name="mydb",
        pool_size=10
    )
    
    db = PostgresDatabase(config)
    
    # Create tables
    async with db._engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Insert user
    async with db.session() as session:
        user = User(name="John Doe", email="john@example.com")
        session.add(user)
    # Automatically commits
    
    # Query users
    async with db.session() as session:
        result = await session.execute(select(User))
        users = result.scalars().all()
        for user in users:
            print(f"{user.name} - {user.email}")
    
    await db.dispose()

asyncio.run(main())
```

**API Explanation:**
- `DatabaseConfig`: Configuration with driver, host, port, credentials, pool settings
- `PostgresDatabase(config)`: Creates PostgreSQL connection manager
- `db.session()`: Context manager for database session
- `session.add()`: Add object to session
- Auto-commit on successful exit, auto-rollback on exception
- `db.dispose()`: Close all connections

### Example 2: MySQL Connection
```python
from internal_rdbms import MySQLDatabase, DatabaseConfig

config = DatabaseConfig(
    driver="mysql+aiomysql",
    host="db.example.com",
    port=3306,
    user="root",
    password="secret",
    name="production_db",
    pool_size=20,
    connect_args={"charset": "utf8mb4"}
)

db = MySQLDatabase(config)

async with db.session() as session:
    # Your queries here
    pass

await db.dispose()
```

**API Explanation:**
- `MySQLDatabase`: MySQL-specific implementation
- Uses aiomysql driver for async operations
- `connect_args`: Pass MySQL-specific options (charset, ssl, etc.)

### Example 3: SQLite (Fast Unit Tests)
```python
from internal_rdbms import SQLiteMemDatabase, DatabaseConfig

# In-memory database (perfect for testing)
config = DatabaseConfig(
    driver="sqlite+aiosqlite",
    name=":memory:"
)

db = SQLiteMemDatabase(config)

# Create tables
async with db._engine.begin() as conn:
    await conn.run_sync(Base.metadata.create_all)

# Use database
async with db.session() as session:
    # Fast in-memory operations
    pass

# No dispose needed (in-memory)
```

**API Explanation:**
- `SQLiteMemDatabase`: In-memory SQLite for testing
- No network, no Docker required
- Millisecond speed for tests
- Uses `StaticPool` to reuse single connection
- Data lost after process ends

### Example 4: Transaction Handling
```python
async with db.session() as session:
    try:
        # Multiple operations in transaction
        user1 = User(name="Alice", email="alice@example.com")
        user2 = User(name="Bob", email="bob@example.com")
        
        session.add(user1)
        session.add(user2)
        
        # Simulate error
        if some_condition:
            raise ValueError("Something went wrong")
        
        # Success: auto-commits on exit
    except ValueError:
        # Auto-rollback on exception
        print("Transaction rolled back")
```

**API Explanation:**
- Session context manager provides automatic transaction handling
- Success path: `commit()` called automatically
- Exception path: `rollback()` called automatically
- No manual transaction management needed

---

# internal-aws Examples

## S3 Operations

### Example 1: Upload and Download Files
```python
import asyncio
from internal_aws import S3Client, S3ClientConfig

async def main():
    config = S3ClientConfig(
        bucket_name="my-app-bucket",
        region="us-east-1"
    )
    
    client = S3Client(config)
    
    # Upload file
    await client.upload_file("local-file.txt", "remote/path/file.txt")
    print("File uploaded!")
    
    # Download file
    await client.download_file("remote/path/file.txt", "downloaded.txt")
    print("File downloaded!")
    
    # List objects
    keys = await client.list_objects(prefix="remote/path/")
    print(f"Found {len(keys)} objects")

asyncio.run(main())
```

**API Explanation:**
- `S3ClientConfig`: Configure bucket, region, endpoint (for LocalStack)
- `upload_file(local, remote)`: Upload local file to S3
- `download_file(remote, local)`: Download S3 file to local
- `list_objects(prefix)`: List objects with prefix filter

### Example 2: Working with JSON and Pydantic Models
```python
import asyncio
from pydantic import BaseModel
from internal_aws import S3Client, S3ClientConfig

class Config(BaseModel):
    app_name: str
    version: str
    debug: bool

async def main():
    config_s3 = S3ClientConfig(bucket_name="config-bucket", region="us-east-1")
    client = S3Client(config_s3)
    
    # Save Pydantic model as JSON
    app_config = Config(app_name="MyApp", version="1.0.0", debug=False)
    await client.put_object(
        "config/app.json",
        app_config.model_dump_json(),
        content_type="application/json"
    )
    
    # Load JSON as Pydantic model
    loaded_config = await client.get_object_as_model("config/app.json", Config)
    print(f"App: {loaded_config.app_name}, Version: {loaded_config.version}")
    
    # Simple JSON operations
    data = {"key": "value", "count": 42}
    await client.put_object("data.json", json.dumps(data), content_type="application/json")
    
    loaded_data = await client.get_object_as_json("data.json")
    print(loaded_data)

asyncio.run(main())
```

**API Explanation:**
- `put_object(key, body, content_type, metadata)`: Upload data to S3
- `get_object_as_json(key)`: Download and parse JSON
- `get_object_as_model(key, Model)`: Download and parse to Pydantic model
- Automatic serialization/deserialization

### Example 3: Presigned URLs
```python
# Generate presigned URL for temporary access
download_url = await client.get_presigned_url(
    "private/file.pdf",
    expires_in=3600,  # Valid for 1 hour
    http_method="GET"
)
print(f"Share this URL: {download_url}")

# Generate upload URL
upload_url = await client.get_presigned_url(
    "uploads/new-file.pdf",
    expires_in=300,  # Valid for 5 minutes
    http_method="PUT"
)
print(f"Upload to: {upload_url}")
```

**API Explanation:**
- `get_presigned_url(key, expires_in, http_method)`: Generate temporary URL
- Allows access without AWS credentials
- `expires_in`: Seconds until URL expires
- `http_method`: GET (download), PUT (upload), DELETE

---

## DynamoDB Operations

### Example 1: CRUD Operations with Type Safety
```python
import asyncio
from pydantic import BaseModel
from internal_aws import DynamoTable, DynamoDBConfig

class Product(BaseModel):
    product_id: str
    name: str
    price: float
    in_stock: bool

async def main():
    config = DynamoDBConfig(
        table_name="products",
        region="us-east-1"
    )
    
    table = DynamoTable(
        config,
        Product,
        key_schema=[{"AttributeName": "product_id", "KeyType": "HASH"}],
        attribute_definitions=[{"AttributeName": "product_id", "AttributeType": "S"}]
    )
    
    # Create table (first time only)
    await table.create_table()
    
    # Put item
    product = Product(product_id="prod-123", name="Laptop", price=999.99, in_stock=True)
    await table.put_item(product)
    
    # Get item (type-safe!)
    retrieved = await table.get_item({"product_id": "prod-123"})
    print(f"Product: {retrieved.name}, Price: ${retrieved.price}")
    
    # Update item
    await table.update_item(
        key={"product_id": "prod-123"},
        update_expression="SET price = :price, in_stock = :stock",
        expression_attribute_values={":price": 899.99, ":stock": False}
    )
    
    # Delete item
    await table.delete_item({"product_id": "prod-123"})

asyncio.run(main())
```

**API Explanation:**
- `DynamoTable[T]`: Generic type-safe table client
- `put_item(model)`: Insert Pydantic model or dict
- `get_item(key)`: Returns Pydantic model instance
- `update_item(key, expression, values)`: Update with DynamoDB expressions
- `delete_item(key)`: Delete by primary key

This is Part 1 of EXAMPLES.md - would you like me to continue with DynamoDB queries, SQS operations, and FastAPI examples?


### Example 2: Query and Scan Operations
```python
# Query by partition key
products = await table.query(
    key_condition_expression="product_id = :id",
    expression_attribute_values={":id": "prod-123"}
)

# Query with filter
expensive_products = await table.query(
    key_condition_expression="category = :cat",
    filter_expression="price > :min_price",
    expression_attribute_values={
        ":cat": "electronics",
        ":min_price": 500.0
    }
)

# Scan all items
all_products = await table.scan()

# Scan with filter
in_stock = await table.scan(
    filter_expression="in_stock = :stock",
    expression_attribute_values={":stock": True}
)
```

**API Explanation:**
- `query()`: Query by primary key (efficient)
- `scan()`: Scan entire table (expensive, use sparingly)
- `filter_expression`: Additional filtering
- `expression_attribute_values`: Values for expressions
- Returns list of Pydantic model instances

### Example 3: Batch Operations
```python
# Batch write (up to 25 items)
products = [
    Product(product_id=f"prod-{i}", name=f"Product {i}", price=10.0 * i, in_stock=True)
    for i in range(20)
]
await table.batch_write_items_to_table(products)

# Batch get
keys = [{"product_id": f"prod-{i}"} for i in range(10)]
retrieved_products = await table.batch_get_items_from_table(keys)
print(f"Retrieved {len(retrieved_products)} products")
```

**API Explanation:**
- `batch_write_items_to_table(items)`: Write up to 25 items at once
- `batch_get_items_from_table(keys)`: Get up to 100 items at once
- Much more efficient than individual operations
- Automatically handles DynamoDB serialization

---

## SQS Operations

### Example 1: Send and Receive Messages
```python
import asyncio
from internal_aws import SQSClient, SQSConfig

async def main():
    config = SQSConfig(
        queue_url="https://sqs.us-east-1.amazonaws.com/123456789012/my-queue",
        region="us-east-1"
    )
    
    client = SQSClient(config)
    
    # Send message
    response = await client.send_message("Hello, SQS!")
    print(f"Message ID: {response['MessageId']}")
    
    # Receive messages
    messages = await client.receive_message(
        max_number_of_messages=10,
        wait_time_seconds=20  # Long polling
    )
    
    for msg in messages:
        print(f"Message: {msg['Body']}")
        
        # Delete after processing
        await client.delete_message(msg['ReceiptHandle'])

asyncio.run(main())
```

**API Explanation:**
- `send_message(body)`: Send string, dict, or Pydantic model
- `receive_message(max, wait_time)`: Long polling for messages
- `wait_time_seconds`: How long to wait for messages (0-20)
- `delete_message(receipt_handle)`: Delete after processing

### Example 2: Working with Pydantic Models
```python
from pydantic import BaseModel
from internal_aws import SQSClient, SQSConfig

class Task(BaseModel):
    task_id: str
    action: str
    priority: int

async def main():
    client = SQSClient(config)
    
    # Send Pydantic model (auto-serialized to JSON)
    task = Task(task_id="task-123", action="process_data", priority=1)
    await client.send_message(task)
    
    # Receive and parse
    messages = await client.receive_message()
    for msg in messages:
        import json
        task_data = json.loads(msg["Body"])
        task = Task(**task_data)
        print(f"Task {task.task_id}: {task.action} (priority {task.priority})")
        
        await client.delete_message(msg["ReceiptHandle"])

asyncio.run(main())
```

**API Explanation:**
- Pydantic models automatically serialized to JSON
- `model.model_dump_json()` called internally
- Parse back using `json.loads()` and `Model(**data)`

### Example 3: Batch Operations
```python
# Send batch (up to 10 messages)
messages = [f"Message {i}" for i in range(10)]
response = await client.send_message_batch(messages)
print(f"Successful: {len(response['Successful'])}")
print(f"Failed: {len(response['Failed'])}")

# Delete batch
entries = [
    {"Id": str(i), "ReceiptHandle": msg["ReceiptHandle"]}
    for i, msg in enumerate(messages)
]
await client.delete_message_batch(entries)
```

**API Explanation:**
- `send_message_batch(messages)`: Send up to 10 messages
- Returns `Successful` and `Failed` lists
- `delete_message_batch(entries)`: Delete multiple messages

### Example 4: Message Processing with Handler
```python
import asyncio

# Define message handler
async def process_task(message):
    """Process a single message."""
    import json
    data = json.loads(message["Body"])
    print(f"Processing: {data}")
    
    # Your processing logic here
    await asyncio.sleep(1)
    
    print(f"Completed: {data}")

# Process messages
results = await client.process_messages(
    handler=process_task,
    max_number_of_messages=10,
    wait_time_seconds=20,
    auto_delete=True  # Auto-delete on success
)

# Check results
for result in results:
    if result["success"]:
        print(f"✓ Processed {result['message']['MessageId']}")
    else:
        print(f"✗ Failed: {result['error']}")
```

**API Explanation:**
- `process_messages(handler)`: Receive and process in one call
- `handler`: Sync or async function
- `auto_delete=True`: Delete messages after successful processing
- Returns list of results with success/failure status

### Example 5: Long-Running Consumer
```python
from internal_aws import SQSConsumer
import asyncio

async def handle_message(message):
    """Handle each message."""
    print(f"Received: {message['Body']}")
    # Process message
    await asyncio.sleep(2)

# Create consumer
consumer = SQSConsumer(
    queue_url="https://sqs.us-east-1.amazonaws.com/123/my-queue",
    region="us-east-1",
    handler=handle_message,
    max_messages=10,
    wait_time=20,  # Long polling
    auto_delete=True
)

# Run consumer (blocks until stopped)
try:
    await consumer.start()
except KeyboardInterrupt:
    await consumer.stop()
```

**API Explanation:**
- `SQSConsumer`: Long-running message consumer
- Continuously polls queue and processes messages
- `start()`: Begin consuming (blocks)
- `stop()`: Graceful shutdown
- Handles failures and retries automatically

---

# internal-fastapi Examples

## FastAPI Application Setup

### Example 1: Basic FastAPI App
```python
from fastapi import FastAPI
from internal_fastapi import FastAPISetup, APIConfig, Environment

# Configure API
config = APIConfig(
    title="My API",
    version="1.0.0",
    env=Environment.DEV,
    debug=True,
    cors_origins=["http://localhost:3000"]
)

# Create app
setup = FastAPISetup(config)
app = setup.create_fastapi_app()

# Add routes
@app.get("/")
async def root():
    return {"message": "Hello, World!"}

@app.get("/health")
async def health():
    return {"status": "ok"}

# Run with uvicorn
# uvicorn main:app --reload
```

**API Explanation:**
- `APIConfig`: Configure title, version, environment, CORS
- `FastAPISetup`: Creates configured FastAPI app
- Automatically sets up CORS, lifecycle management
- `create_fastapi_app()`: Returns configured FastAPI instance

### Example 2: With Background Services
```python
from fastapi import FastAPI
from internal_fastapi import FastAPISetup, APIConfig, LifecycleManager
from internal_base import AsyncService
import asyncio

class MetricsCollector(AsyncService):
    """Collect metrics periodically."""
    
    def __init__(self):
        super().__init__()
        self._task = None
    
    async def _start(self):
        self._task = asyncio.create_task(self._collect_loop())
    
    async def _stop(self):
        if self._task:
            self._task.cancel()
    
    async def _health_check(self):
        return True
    
    async def _collect_loop(self):
        while True:
            print("Collecting metrics...")
            await asyncio.sleep(60)

# Setup handler
async def setup_services():
    """Initialize background services."""
    metrics = MetricsCollector()
    return [metrics]

# Create app
config = APIConfig(title="My API")
setup = FastAPISetup(config, setup_handler=setup_services)
app = setup.create_fastapi_app()

# Services start automatically on app startup
# Services stop automatically on app shutdown
```

**API Explanation:**
- `setup_handler`: Async function returning list of services
- Services must implement `BackgroundServiceProtocol`
- Automatically started on app startup
- Automatically stopped on app shutdown
- Signal handling (SIGTERM, SIGINT) included

---

## Authentication

### Example 1: Token Authentication
```python
from fastapi import FastAPI, Depends
from internal_fastapi import AppTokenConfig, setup_token_auth

app = FastAPI()

# Configure token auth
config = AppTokenConfig(
    header_name="X-API-Key",
    tokens={
        "mobile-app": "secret-token-1",
        "web-app": "secret-token-2",
        "admin": "admin-secret-token"
    },
    exclude_paths={
        "/health",
        "/docs",
        "/openapi.json"
    }
)

# Setup auth
auth = setup_token_auth(app, config)

# Protected endpoint
@app.get("/api/data")
async def get_data(app_name: str = Depends(auth)):
    return {
        "message": f"Hello {app_name}!",
        "data": [1, 2, 3]
    }

# Excluded endpoint (no auth required)
@app.get("/health")
async def health():
    return {"status": "ok"}
```

**API Explanation:**
- `AppTokenConfig`: Configure tokens and excluded paths
- `tokens`: Map of app names to tokens
- `exclude_paths`: Paths that don't require auth
- `setup_token_auth()`: Returns auth dependency
- Use `Depends(auth)` to get authenticated app name

### Example 2: Token Middleware
```python
from fastapi import FastAPI, Request
from internal_fastapi import AppTokenConfig, apply_token_auth_middleware

app = FastAPI()

config = AppTokenConfig(
    tokens={"app1": "secret1"},
    exclude_paths={"/health", "/docs"}
)

# Apply middleware (checks all requests)
apply_token_auth_middleware(app, config)

@app.get("/api/protected")
async def protected(request: Request):
    # Access app name from request state
    app_name = request.state.app_name
    return {"authenticated_as": app_name}
```

**API Explanation:**
- `apply_token_auth_middleware()`: Applies middleware to all routes
- Automatically checks token on every request
- Excluded paths bypass auth
- `request.state.app_name`: Get authenticated app name

### Example 3: Path Exclusion with Glob Patterns
```python
config = AppTokenConfig(
    tokens={"app": "token"},
    exclude_paths={
        "/health",
        "/docs",
        "/api/public/*",      # Exclude all /api/public/**
        "/webhooks/*",        # Exclude all webhooks
        "/static/*.css"       # Exclude CSS files
    }
)

# These paths DON'T require auth:
# /health
# /api/public/info
# /api/public/status
# /webhooks/stripe
# /static/main.css

# These paths DO require auth:
# /api/users
# /api/admin
```

**API Explanation:**
- Glob patterns supported: `*` (wildcard), `?` (single char)
- Converted to regex for matching
- Flexible path exclusion

---

## Health Checks

### Example 1: Basic Health Check
```python
from fastapi import FastAPI
from internal_fastapi import create_health_endpoint

app = FastAPI()

# Create health endpoint
health = create_health_endpoint(app, path="/health")

# Returns: {"status": "healthy", "details": {}}
```

**API Explanation:**
- `create_health_endpoint(app, path)`: Create health endpoint
- Returns HealthCheck instance for adding checks
- Automatic endpoint at specified path

### Example 2: Health Checks with Custom Checks
```python
from fastapi import FastAPI
from internal_fastapi import create_health_endpoint

app = FastAPI()

# Sync check
def check_database():
    """Check database connection."""
    # Check DB connection
    return {"status": "connected", "latency_ms": 5}

# Async check
async def check_redis():
    """Check Redis connection."""
    # Async check
    return {"status": "connected", "keys": 100}

# Create health endpoint with checks
health = create_health_endpoint(
    app,
    path="/health",
    checks=[
        ("database", check_database),
        ("redis", check_redis)
    ]
)

# Add more checks later
def check_external_api():
    return {"status": "ok", "response_time": 150}

health.add_check("external_api", check_external_api)

# Returns:
# {
#   "status": "healthy",
#   "details": {
#     "database": {"status": "connected", "latency_ms": 5},
#     "redis": {"status": "connected", "keys": 100},
#     "external_api": {"status": "ok", "response_time": 150}
#   }
# }
```

**API Explanation:**
- `checks`: List of (name, function) tuples
- Functions can be sync or async
- `add_check(name, func)`: Add check dynamically
- Overall status "healthy" if all checks pass
- Status "unhealthy" if any check fails

---

## Logging Middleware

### Example 1: Request/Response Logging
```python
from fastapi import FastAPI
from internal_fastapi import LoggingMiddleware

app = FastAPI()

# Add logging middleware
app.add_middleware(LoggingMiddleware)

@app.get("/api/users")
async def get_users():
    return {"users": []}

# Logs:
# INFO - Request: GET /api/users from 127.0.0.1
# INFO - Response: GET /api/users - 200 OK (15.2ms)

# Response includes header: X-Process-Time: 15.2ms
```

**API Explanation:**
- `LoggingMiddleware`: Logs all requests/responses
- Includes timing information
- Adds `X-Process-Time` header to responses
- Logs errors with full traceback

---

## Complete Example: Production-Ready API

```python
from fastapi import FastAPI, Depends
from internal_fastapi import (
    FastAPISetup,
    APIConfig,
    Environment,
    AppTokenConfig,
    apply_token_auth_middleware,
    create_health_endpoint,
    LoggingMiddleware
)
from internal_base import LoggingConfig, LogFormat, configure_logging

# Configure logging
log_config = LoggingConfig(
    format=LogFormat.JSON,
    level="INFO"
)
configure_logging(log_config)

# Configure API
api_config = APIConfig(
    title="Production API",
    version="1.0.0",
    env=Environment.PROD,
    debug=False,
    reload=False,
    workers=4,
    cors_origins=["https://app.example.com"]
)

# Setup app
setup = FastAPISetup(api_config, log_config)
app = setup.create_fastapi_app()

# Add logging middleware
app.add_middleware(LoggingMiddleware)

# Setup authentication
auth_config = AppTokenConfig(
    tokens={
        "mobile": "prod-mobile-token",
        "web": "prod-web-token"
    },
    exclude_paths={
        "/health",
        "/docs",
        "/api/public/*"
    }
)
apply_token_auth_middleware(app, auth_config)

# Health checks
def check_db():
    return {"status": "connected"}

async def check_redis():
    return {"status": "connected"}

health = create_health_endpoint(
    app,
    path="/health",
    checks=[
        ("database", check_db),
        ("cache", check_redis)
    ]
)

# Routes
@app.get("/api/users")
async def get_users():
    return {"users": []}

@app.get("/api/public/status")
async def public_status():
    return {"status": "operational"}

# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

**Features:**
- ✅ JSON logging for production
- ✅ CORS configured
- ✅ Token authentication with path exclusions
- ✅ Health checks (database, cache)
- ✅ Request/response logging with timing
- ✅ Multiple workers for production
- ✅ Lifecycle management
- ✅ OpenAPI documentation

---

## Summary

All examples follow these principles:
- **Async-first**: All I/O operations use async/await
- **Type-safe**: Pydantic models everywhere
- **Context managers**: Proper resource cleanup
- **Error handling**: Exceptions properly propagated
- **Production-ready**: Real-world configurations

**Next Steps:**
1. Review `tests/README.md` for testing examples
2. See `ARCHITECTURE.md` for complete API reference
3. Check inline docstrings for detailed documentation

