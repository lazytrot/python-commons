# Python Commons - Complete Package Documentation

This document provides a comprehensive overview of all packages in the python-commons repository, including directory structures, class definitions, and function signatures.

---

## Table of Contents

1. [Package Overview](#package-overview)
2. [internal-base](#internal-base)
3. [internal-aws](#internal-aws)
4. [internal-fastapi](#internal-fastapi)
5. [internal-http](#internal-http)
6. [internal-rdbms](#internal-rdbms)

---

## Package Overview

The python-commons repository contains 5 main packages:

| Package | Description |
|---------|-------------|
| **internal-base** | Base utilities including logging, async services, and YAML settings |
| **internal-aws** | AWS service integrations (S3, DynamoDB, SQS) |
| **internal-fastapi** | FastAPI utilities including auth, health checks, and lifecycle management |
| **internal-http** | HTTP client with authentication and retry logic |
| **internal-rdbms** | Database connection managers for MySQL, PostgreSQL, and SQLite |

---

# internal-base

Base utilities package providing logging, async service management, and configuration handling.

## Directory Structure

```
internal_base/
├── __init__.py
├── logging/
│   ├── __init__.py
│   ├── config.py
│   └── logger.py
├── service/
│   ├── __init__.py
│   ├── protocol.py
│   └── async_service.py
└── settings/
    ├── __init__.py
    └── yaml_base_settings.py
```

## Module Documentation

### internal_base/logging/__init__.py

**Functions:**
```python
def getLogger(name: str)
def configure_logging(logger_settings: Optional[LoggingConfig] = None)
```

### internal_base/logging/config.py

**Classes:**

```python
class LogFormat(str, Enum):
    """Logging format enumeration."""

    Methods:
    - def __str__(self) -> str

class LoggingConfig(BaseModel):
    """Logging configuration model."""

    Fields:
    - format: LogFormat
    - level: str
    - propagate: bool
```

### internal_base/logging/logger.py

**Functions:**
```python
def getLogger(name: str) -> logging.Logger
def configure_logging(logger_settings: Optional[LoggingConfig] = None) -> None
```

### internal_base/service/protocol.py

**Classes:**

```python
class ServiceState(str, Enum):
    """Service state enumeration."""

    Methods:
    - def __str__(self) -> str

class BackgroundServiceProtocol(Protocol):
    """Protocol for background services (runtime_checkable)."""

    Properties:
    - def state(self) -> ServiceState

    Methods:
    - async def start(self) -> None
    - async def stop(self) -> None
    - async def is_healthy(self) -> bool
```

### internal_base/service/async_service.py

**Classes:**

```python
class AsyncService(ABC):
    """Abstract base class for async services."""

    Methods:
    - def __init__(self, name: Optional[str] = None)

    Properties:
    - def state(self) -> ServiceState

    Public Methods:
    - async def start(self) -> None
    - async def stop(self) -> None
    - async def is_healthy(self) -> bool
    - async def __aenter__(self) -> "AsyncService"
    - async def __aexit__(self, exc_type, exc_val, exc_tb) -> None

    Abstract Methods (must be implemented by subclasses):
    - async def _start(self) -> None
    - async def _stop(self) -> None
    - async def _health_check(self) -> bool
```

### internal_base/settings/yaml_base_settings.py

**Dependencies:**
- pydantic-settings>=2.0.0
- pydantic-settings-extra-sources>=0.1.0 (for YAML support)

**Classes:**

```python
class EnvAwareYamlConfigSettingsSource(YamlConfigSettingsSource):
    """YAML settings source with environment variable substitution.

    Uses pydantic-settings-extra-sources for advanced YAML configuration loading
    with environment variable substitution support.
    """

    Methods:
    - def _read_file(self, path: Path) -> dict[str, Any]
    - def _substitute_env_vars(self, content: str) -> str
    - def _mask_sensitive_data(self, content: str, error: str, non_masked_length: int = 0) -> str

class EnvYamlSettings(BaseSettings):
    """Base settings class with YAML and environment variable support.

    Leverages pydantic-settings-extra-sources to provide:
    - YAML configuration file loading
    - Environment variable override support
    - Multiple configuration source priority handling
    - Type-safe configuration with Pydantic validation
    """

    Methods:
    - @classmethod def settings_customise_sources(cls, settings_cls: Type[BaseSettings], init_settings: PydanticBaseSettingsSource, env_settings: PydanticBaseSettingsSource, dotenv_settings: PydanticBaseSettingsSource, file_secret_settings: PydanticBaseSettingsSource) -> Tuple[PydanticBaseSettingsSource, ...]
```

**Settings Priority (highest to lowest):**
1. Explicit initialization parameters
2. Environment variables
3. YAML configuration file
4. .env file
5. Default field values

## Summary

- **Total Files:** 9
- **Total Classes:** 8
- **Total Functions:** 4
- **Key Features:** Logging configuration, async service lifecycle management, YAML-based settings with env var support

---

# internal-aws

AWS service integrations providing async clients for S3, DynamoDB, and SQS.

## Directory Structure

```
internal_aws/
├── __init__.py
├── auth/
│   └── credentials.py
├── dynamodb/
│   ├── __init__.py
│   └── table.py
├── s3/
│   ├── __init__.py
│   └── client.py
└── sqs/
    ├── __init__.py
    ├── client.py
    └── consumer.py
```

## Module Documentation

### internal_aws/auth/credentials.py

**Classes:**

```python
class AWSCredentials(BaseModel):
    """AWS credentials model."""

    Methods:
    - def to_dict(self) -> Dict[str, str]

class CredentialProvider(ABC):
    """Abstract credential provider."""

    Methods:
    - async def get_credentials(self) -> Optional[AWSCredentials]

class ExplicitCredentialProvider(CredentialProvider):
    """Explicit credential provider with hardcoded values."""

    Methods:
    - def __init__(self, access_key_id: str, secret_access_key: str, session_token: Optional[str] = None)
    - async def get_credentials(self) -> AWSCredentials

class EnvironmentCredentialProvider(CredentialProvider):
    """Credential provider from environment variables."""

    Methods:
    - async def get_credentials(self) -> Optional[AWSCredentials]

class ProfileCredentialProvider(CredentialProvider):
    """Credential provider from AWS profile."""

    Methods:
    - def __init__(self, profile_name: str = "default")
    - async def get_credentials(self) -> Optional[AWSCredentials]

class DefaultCredentialProvider(CredentialProvider):
    """Default credential provider (tries multiple sources)."""

    Methods:
    - def __init__(self, profile_name: str = "default")
    - async def get_credentials(self) -> Optional[AWSCredentials]
```

### internal_aws/dynamodb/table.py

**Classes:**

```python
class DynamoDBConfig(BaseModel):
    """DynamoDB configuration."""

    Fields:
    - table_name: str
    - region: str
    - endpoint_url: Optional[str]

class DynamoTable(Generic[T]):
    """Generic DynamoDB table client."""

    Methods:
    - def __init__(self, config: DynamoDBConfig, model_class: Type[T], credential_provider: Optional[CredentialProvider] = None, key_schema: Optional[List[Dict[str, str]]] = None, attribute_definitions: Optional[List[Dict[str, str]]] = None, provisioned_throughput: Optional[Dict[str, int]] = None)
    - async def _get_credentials(self)
    - async def _get_client_kwargs(self) -> Dict[str, Any]
    - async def get_client(self)  # async context manager
    - async def create_table(self) -> Dict[str, Any]
    - async def delete_table(self) -> Dict[str, Any]
    - async def put_item(self, item: Union[T, Dict[str, Any]]) -> Dict[str, Any]
    - async def get_item(self, key: Dict[str, Any]) -> Optional[T]
    - async def delete_item(self, key: Dict[str, Any]) -> Dict[str, Any]
    - async def query(self, key_condition_expression: str, expression_attribute_values: Dict[str, Any], expression_attribute_names: Optional[Dict[str, str]] = None, filter_expression: Optional[str] = None, index_name: Optional[str] = None, limit: Optional[int] = None, scan_index_forward: bool = True) -> List[T]
    - async def scan(self, filter_expression: Optional[str] = None, expression_attribute_values: Optional[Dict[str, Any]] = None, expression_attribute_names: Optional[Dict[str, str]] = None, index_name: Optional[str] = None, limit: Optional[int] = None) -> List[T]
    - async def update_item(self, key: Dict[str, Any], update_expression: str, expression_attribute_values: Dict[str, Any], expression_attribute_names: Optional[Dict[str, str]] = None, condition_expression: Optional[str] = None, return_values: str = "UPDATED_NEW") -> Dict[str, Any]
    - async def batch_get_items(self, keys: List[Dict[str, Any]], consistent_read: bool = False, projection_expression: Optional[str] = None) -> Dict[str, List[Dict[str, Any]]]
    - async def batch_write_items(self, items_to_put: Optional[List[Dict[str, Any]]] = None, items_to_delete: Optional[List[Dict[str, Any]]] = None) -> Dict[str, List[Dict[str, Any]]]
    - async def batch_write_items_to_table(self, items: List[Union[T, Dict[str, Any]]]) -> Dict[str, Any]
    - async def batch_get_items_from_table(self, keys: List[Dict[str, Any]], consistent_read: bool = False) -> List[T]
    - def _serialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]
    - def _serialize_value(self, value: Any) -> Dict[str, Any]
    - def _deserialize_item(self, item: Dict[str, Any]) -> Dict[str, Any]
    - def _deserialize_value(self, value: Dict[str, Any]) -> Any
```

### internal_aws/s3/client.py

**Classes:**

```python
class S3ClientConfig(BaseModel):
    """S3 client configuration."""

    Fields:
    - bucket_name: str
    - region: str
    - endpoint_url: Optional[str]

class S3Client:
    """S3 client for file operations."""

    Methods:
    - def __init__(self, config: S3ClientConfig, credential_provider: Optional[CredentialProvider] = None)
    - async def _get_credentials(self)
    - async def _get_client_kwargs(self) -> Dict[str, Any]
    - async def get_client(self)  # async context manager
    - async def upload_file(self, local_path: str, s3_key: str, extra_args: Optional[Dict[str, Any]] = None) -> bool
    - async def upload_fileobj(self, fileobj: BinaryIO, s3_key: str, extra_args: Optional[Dict[str, Any]] = None) -> bool
    - async def download_file(self, s3_key: str, local_path: str) -> bool
    - async def list_objects(self, prefix: str = "", delimiter: str = "", max_keys: int = 1000) -> List[str]
    - async def get_object(self, s3_key: str) -> Dict[str, Any]
    - async def get_object_body(self, s3_key: str) -> bytes
    - async def delete_object(self, s3_key: str) -> Dict[str, Any]
    - async def delete_objects(self, s3_keys: List[str]) -> Dict[str, Any]
    - async def get_presigned_url(self, s3_key: str, expires_in: int = 3600, http_method: str = "GET") -> str
    - async def copy_object(self, source_key: str, target_key: str, source_bucket: Optional[str] = None, metadata: Optional[Dict[str, str]] = None, metadata_directive: str = "COPY") -> Dict[str, Any]
    - async def put_object(self, s3_key: str, body: Union[bytes, str, BinaryIO], content_type: Optional[str] = None, metadata: Optional[Dict[str, str]] = None) -> Dict[str, Any]
    - async def get_object_as_bytes(self, s3_key: str) -> bytes
    - async def get_object_as_string(self, s3_key: str, encoding: str = 'utf-8') -> str
    - async def get_object_as_json(self, s3_key: str) -> Dict[str, Any]
    - async def get_object_as_model(self, s3_key: str, model_class: Type[T]) -> T
```

### internal_aws/sqs/client.py

**Type Definitions:**

```python
SQSResponseMetadata = TypedDict(...)
SQSSendMessageResponse = TypedDict(...)
SQSBatchResultErrorEntry = TypedDict(...)
SQSBatchResultSuccessEntry = TypedDict(...)
SQSSendMessageBatchResponse = TypedDict(...)
SQSDeleteMessageResponse = TypedDict(...)
SQSDeleteMessageBatchResponse = TypedDict(...)
SQSPurgeQueueResponse = TypedDict(...)
SQSMessageAttributes = TypedDict(...)
SQSMessage = TypedDict(...)
SQSProcessMessageResult = TypedDict(...)
```

**Classes:**

```python
class SQSConfig(BaseModel):
    """SQS configuration."""

    Fields:
    - queue_url: str
    - region: str
    - endpoint_url: Optional[str]

class SQSClient:
    """SQS client for queue operations."""

    Methods:
    - def __init__(self, config: SQSConfig, credential_provider: Optional[CredentialProvider] = None)
    - async def _get_credentials(self) -> Optional[AWSCredentials]
    - async def _get_client_kwargs(self) -> Dict[str, Any]
    - async def get_client(self)  # async context manager
    - async def create_queue(self, queue_name: str, attributes: Optional[Dict[str, str]] = None) -> str
    - async def send_message(self, message: Union[str, Dict[str, Any], BaseModel], message_attributes: Optional[Dict[str, Dict[str, str]]] = None, delay_seconds: Optional[int] = None) -> SQSSendMessageResponse
    - async def send_message_batch(self, messages: List[Union[str, Dict[str, Any], BaseModel]], message_attributes: Optional[List[Dict[str, Dict[str, str]]]] = None, delay_seconds: Optional[int] = None) -> SQSSendMessageBatchResponse
    - async def receive_message(self, max_number_of_messages: int = 1, wait_time_seconds: Optional[int] = None, visibility_timeout: Optional[int] = None, model_class: Optional[Type[T]] = None) -> List[SQSMessage]
    - async def delete_message(self, receipt_handle: str) -> SQSDeleteMessageResponse
    - async def delete_message_batch(self, entries: List[Dict[str, str]]) -> SQSDeleteMessageBatchResponse
    - async def purge_queue(self) -> SQSPurgeQueueResponse
    - async def process_messages(self, handler: Callable[[SQSMessage], Any], max_number_of_messages: int = 10, wait_time_seconds: Optional[int] = None, visibility_timeout: Optional[int] = None, model_class: Optional[Type[T]] = None, auto_delete: bool = True) -> List[SQSProcessMessageResult]
```

### internal_aws/sqs/consumer.py

**Classes:**

```python
class SQSConsumer:
    """Long-polling SQS consumer."""

    Methods:
    - def __init__(self, queue_url: str, region: str, handler: Callable[[SQSMessage], Any], max_messages: int = 10, wait_time: int = 20, visibility_timeout: int = 30, endpoint_url: Optional[str] = None, credential_provider: Optional[CredentialProvider] = None, polling_interval: float = 0.1, model_class: Optional[Type[T]] = None, auto_delete: bool = True)
    - async def start(self) -> None
    - async def stop(self) -> None
    - async def process_batch(self, batch_size: int = 10) -> List[SQSProcessMessageResult]
```

## Summary

- **Total Files:** 9
- **Total Classes:** 15
- **Total Methods:** 70+
- **Key Features:** Full async/await, credential management, S3/DynamoDB/SQS operations, batch operations

---

# internal-fastapi

FastAPI utilities for authentication, health checks, logging, and lifecycle management.

## Directory Structure

```
internal_fastapi/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── api_service.py
│   ├── config.py
│   ├── fastapi.py
│   └── lifecycle_manager.py
├── auth/
│   ├── __init__.py
│   ├── config.py
│   └── middleware.py
├── health/
│   ├── __init__.py
│   └── endpoint.py
└── logging/
    ├── __init__.py
    └── middleware.py
```

## Module Documentation

### internal_fastapi/api/api_service.py

**Classes:**

```python
class APIService(ABC):
    """Abstract API service base class."""

    Methods:
    - def __init__(self, app: FastAPI, name: Optional[str] = None)
    - def _setup_routes(self) -> None  # abstract method
```

### internal_fastapi/api/config.py

**Classes:**

```python
class Environment(str, Enum):
    """Environment enumeration."""

    Values:
    - DEV = "dev"
    - STAGE = "stage"
    - PROD = "prod"

class APIConfig(BaseModel):
    """API configuration."""

    Fields:
    - enabled: bool = True
    - env: Environment = Environment.DEV
    - title: str = "Agent Framework API"
    - description: str = "API for interacting with the agent framework"
    - version: str = "1.0.0"
    - host: str = "0.0.0.0"
    - port: int = 8000
    - reload: bool = True
    - workers: int = 1
    - debug: bool = True
    - cors_origins: List[str] = ["*"]

    Methods:
    - def validate_header_name(cls, v: str) -> str  # validator
```

### internal_fastapi/api/fastapi.py

**Classes:**

```python
class FastAPISetup:
    """FastAPI application setup and configuration."""

    Methods:
    - def __init__(self, api_config: APIConfig, log_config: LoggingConfig, setup_handler: Callable[[], Awaitable[List[BackgroundServiceProtocol]]])
    - def create_fastapi_app(self) -> FastAPI
```

### internal_fastapi/api/lifecycle_manager.py

**Classes:**

```python
class LifecycleManager:
    """Service lifecycle manager for FastAPI."""

    Methods:
    - def __init__(self)
    - def add_service(self, service: BackgroundServiceProtocol) -> None
    - def set_setup_handler(self, handler: Callable[[], Awaitable[List[BackgroundServiceProtocol]]]) -> None
    - async def _handle_shutdown(self, sig: signal.Signals) -> None
    - async def start(self) -> None
    - async def stop(self) -> None
    - async def lifespan(self) -> AsyncIterator[None]
    - def fastapi_lifespan(self, setup_handler: Optional[Callable[[], Awaitable[List[BackgroundServiceProtocol]]]] = None) -> Callable[[FastAPI], AsyncIterator[None]]

    Properties:
    - def status(self) -> ServiceState
```

### internal_fastapi/auth/config.py

**Classes:**

```python
class AppTokenConfig(BaseModel):
    """App token authentication configuration."""

    Fields:
    - header_name: str = "X-App-Token"
    - tokens: Dict[str, str] = {}
    - enabled: bool = True
    - exclude_paths: Set[str] = set()

    Methods:
    - def validate_header_name(cls, v: str) -> str  # validator
```

### internal_fastapi/auth/middleware.py

**Functions:**

```python
def add_api_key_security_scheme(app: FastAPI, header_name: str, enabled: bool = True) -> None
def setup_token_auth(app: FastAPI, settings: Optional[AppTokenConfig] = None) -> AppTokenAuth
def apply_token_auth_middleware(app: FastAPI, settings: Optional[AppTokenConfig] = None, on_missing_token: Optional[Callable[[Request], Awaitable[Response]]] = None, on_invalid_token: Optional[Callable[[Request, str], Awaitable[Response]]] = None) -> None
def setup_app_token_auth(app: FastAPI, settings: Optional[AppTokenConfig] = None) -> AppTokenAuth  # alias
```

**Classes:**

```python
class AppTokenAuth:
    """Token authentication handler."""

    Methods:
    - def __init__(self, settings: Optional[AppTokenConfig] = None)
    - async def __call__(self, request: Request, api_key: Optional[str] = None) -> Optional[str]
    - def _is_path_excluded(self, path: str) -> bool
    - def _convert_pattern_to_regex(self, pattern: str) -> re.Pattern

class TokenAuthMiddleware(BaseHTTPMiddleware):
    """Token authentication middleware."""

    Methods:
    - def __init__(self, app: Any, settings: Optional[AppTokenConfig] = None, on_missing_token: Optional[Callable[[Request], Awaitable[Response]]] = None, on_invalid_token: Optional[Callable[[Request, str], Awaitable[Response]]] = None, setup_openapi_schema: bool = True)
    - def _setup_openapi_schema(self, app: FastAPI) -> None
    - async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response
    - def _is_path_excluded(self, path: str) -> bool
```

### internal_fastapi/health/endpoint.py

**Type Aliases:**

```python
HealthCheckFunc = Callable[[], Union[Awaitable[Dict[str, Any]], Dict[str, Any]]]
```

**Functions:**

```python
def create_health_endpoint(app: FastAPI, path: str = "/health", include_in_schema: bool = False, checks: Optional[List[Tuple[str, HealthCheckFunc]]] = None) -> HealthCheck
def asyncio_is_coroutine_function(func: Callable) -> bool
```

**Classes:**

```python
class HealthResponse(BaseModel):
    """Health check response model."""

    Fields:
    - status: str
    - details: Dict[str, Any] = {}

class HealthCheck:
    """Health check manager."""

    Methods:
    - def __init__(self, app: Optional[FastAPI] = None, path: str = "/health")
    - def add_check(self, name: str, check_func: HealthCheckFunc) -> None
    - def add_to_app(self, app: FastAPI, include_in_schema: bool = False) -> None
```

### internal_fastapi/logging/middleware.py

**Classes:**

```python
class LoggingMiddleware(BaseHTTPMiddleware):
    """Request/response logging middleware."""

    Methods:
    - async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response
```

## Summary

- **Total Files:** 13
- **Total Classes:** 10
- **Total Functions:** 7
- **Total Methods:** 25+
- **Key Features:** Token auth, health checks, lifecycle management, logging middleware, OpenAPI integration

---

# internal-http

HTTP client library with authentication, retry logic, and Pydantic model support.

## Directory Structure

```
internal_http/
├── __init__.py
├── auth/
│   ├── __init__.py
│   └── auth.py
├── client/
│   ├── __init__.py
│   └── http_client.py
└── models/
    ├── __init__.py
    └── config.py
```

## Module Documentation

### internal_http/auth/auth.py

**Classes:**

```python
class AuthBase:
    """Base authentication class."""

    Methods:
    - def auth_flow(self, request: httpx.Request) -> httpx.Request

class BearerAuth(AuthBase):
    """Bearer token authentication."""

    Methods:
    - def __init__(self, token: str)
    - def auth_flow(self, request: httpx.Request) -> httpx.Request

class BasicAuth(AuthBase):
    """HTTP Basic authentication."""

    Methods:
    - def __init__(self, username: str, password: str)
    - def auth_flow(self, request: httpx.Request) -> httpx.Request

class ApiKeyAuth(AuthBase):
    """API key authentication."""

    Methods:
    - def __init__(self, api_key: str, header_name: str = "X-API-Key", prefix: Optional[str] = None)
    - def auth_flow(self, request: httpx.Request) -> httpx.Request
```

### internal_http/models/config.py

**Classes:**

```python
class RetryConfig(BaseModel):
    """Retry configuration."""

    Fields:
    - max_attempts: int = 3
    - retry_statuses: List[int] = [500, 502, 503, 504]
    - retry_methods: List[str] = ["GET", "HEAD", "PUT", "DELETE", "OPTIONS", "TRACE"]
    - backoff_factor: float = 0.5
    - jitter: bool = True
    - retry_exceptions: List[Exception] = []

class AuthConfig(BaseModel):
    """Authentication configuration."""

    Fields:
    - auth: Optional[Any] = None
    - refresh_token: Optional[str] = None
    - refresh_callback: Optional[Callable[[], str]] = None
```

### internal_http/client/http_client.py

**Classes:**

```python
class HttpClientError(Exception):
    """HTTP client exception."""

    Methods:
    - def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[httpx.Response] = None)

class HttpClient:
    """Async HTTP client with retry and auth support."""

    Methods:
    - def __init__(self, base_url: str = "", timeout: Union[float, httpx.Timeout] = 10.0, retries: Optional[Union[int, RetryConfig]] = None, auth_config: Optional[AuthConfig] = None, default_headers: Optional[Dict[str, str]] = None, verify_ssl: bool = True, follow_redirects: bool = True)
    - async def __aenter__(self)
    - async def __aexit__(self, exc_type, exc_val, exc_tb)
    - async def client(self) -> httpx.AsyncClient  # property/context manager
    - def _should_retry(self, response: httpx.Response) -> bool
    - def _prepare_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> Dict[str, Any]
    - async def _execute_request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def request(self, method: str, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def get(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def post(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def put(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def patch(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def delete(self, url: str, headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> httpx.Response
    - async def get_model(self, url: str, response_model: Type[T], headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> T
    - async def post_model(self, url: str, response_model: Type[T], headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> T
    - async def put_model(self, url: str, response_model: Type[T], headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> T
    - async def patch_model(self, url: str, response_model: Type[T], headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> T
    - async def delete_model(self, url: str, response_model: Type[T], headers: Optional[Dict[str, str]] = None, **kwargs: Any) -> T
```

## Summary

- **Total Files:** 7
- **Total Classes:** 9
- **Total Methods:** 26+
- **Key Features:** Multiple auth strategies, configurable retry logic, Pydantic model integration, async/await

---

# internal-rdbms

Database connection managers for MySQL, PostgreSQL, and SQLite with async support.

## Directory Structure

```
internal_rdbms/
├── __init__.py
├── database/
│   ├── __init__.py
│   ├── config.py
│   ├── db.py
│   ├── mysql.py
│   ├── postgres.py
│   ├── sqlite.py
│   └── sqlite_mem.py
└── utils/
    ├── __init__.py
    └── datetime_utils.py
```

## Module Documentation

### internal_rdbms/database/config.py

**Classes:**

```python
class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    Fields:
    - driver: str = "mysql+aiomysql"
    - host: str = "localhost"
    - port: Optional[int] = None
    - user: Optional[str] = None
    - password: Optional[str] = None
    - name: str = "agent_framework"
    - echo: bool = False
    - pool_size: int = 5
    - max_overflow: int = 10
    - pool_timeout: float = 30.0
    - pool_recycle: int = 1800
    - connect_args: Dict[str, Any] = {}

    Properties:
    - def url(self) -> str  # computed_field
```

### internal_rdbms/database/db.py

**Classes:**

```python
class Database(ABC):
    """Abstract database connection manager."""

    Methods:
    - def __init__(self, settings: DatabaseConfig) -> None
    - def _create_engine(self) -> AsyncEngine  # abstractmethod
    - async def session(self) -> AsyncGenerator[AsyncSession, None]  # asynccontextmanager
    - async def dispose(self) -> None
```

### internal_rdbms/database/mysql.py

**Classes:**

```python
class MySQLDatabase(Database):
    """MySQL database connection manager."""

    Methods:
    - def __init__(self, config: DatabaseConfig) -> None
    - def _create_engine(self) -> AsyncEngine
```

### internal_rdbms/database/postgres.py

**Classes:**

```python
class PostgresDatabase(Database):
    """PostgreSQL database connection manager."""

    Methods:
    - def __init__(self, config: DatabaseConfig) -> None
    - def _create_engine(self) -> AsyncEngine
```

### internal_rdbms/database/sqlite.py

**Classes:**

```python
class SQLiteDatabase(Database):
    """SQLite file-based database connection manager."""

    Methods:
    - def __init__(self, config: DatabaseConfig) -> None
    - def _create_engine(self) -> AsyncEngine
```

### internal_rdbms/database/sqlite_mem.py

**Classes:**

```python
class SQLiteMemDatabase(Database):
    """SQLite in-memory database connection manager."""

    Methods:
    - def __init__(self, config: DatabaseConfig) -> None
    - def _create_engine(self) -> AsyncEngine
```

### internal_rdbms/utils/datetime_utils.py

**Functions:**

```python
def ensure_utc(func: Callable[..., datetime]) -> property
```

**Description:** Decorator that wraps property getters to ensure datetime values are UTC-aware.

## Inheritance Hierarchy

```
ABC (Abstract Base Class)
  └── Database
      ├── MySQLDatabase
      ├── PostgresDatabase
      ├── SQLiteDatabase
      └── SQLiteMemDatabase
```

## Summary

- **Total Files:** 10
- **Total Classes:** 6
- **Total Functions:** 1
- **Total Methods:** 14
- **Key Features:** Async database connections, connection pooling, multiple DB support, UTC datetime utilities

---

## Overall Statistics

| Package | Files | Classes | Functions | Methods |
|---------|-------|---------|-----------|---------|
| internal-base | 9 | 8 | 4 | 19+ |
| internal-aws | 9 | 15 | 0 | 70+ |
| internal-fastapi | 13 | 10 | 7 | 25+ |
| internal-http | 7 | 9 | 0 | 26+ |
| internal-rdbms | 10 | 6 | 1 | 14 |
| **TOTAL** | **48** | **48** | **12** | **154+** |

---

## Common Patterns Across Packages

1. **Async/Await**: All packages use async/await for I/O operations
2. **Pydantic Models**: Configuration and data validation using Pydantic BaseModel
3. **Context Managers**: Proper resource management with context managers
4. **Abstract Base Classes**: Extensibility through ABC pattern
5. **Type Hints**: Full type annotation throughout
6. **Dependency Injection**: Configuration passed via constructors
7. **Protocol/Interface Design**: Clear separation of concerns

---

## Testing Infrastructure

### Testing Principles

**NO MOCKING POLICY**: This project follows a strict "no mocking" principle for maximum reliability and production readiness.

### Test Categories

#### 1. Unit Tests (`tests/unit/`)
- **Purpose**: Fast tests for business logic and pure functions
- **Database**: SQLite in-memory for speed
- **Coverage**: All non-I/O code paths
- **Runtime**: < 1 second per test

#### 2. Integration Tests (`tests/integration/`)
- **Purpose**: Real service integration testing
- **Infrastructure**: testcontainers for all external services
- **NO MOCKS**: Only real service implementations

### Testcontainers Setup

**Required testcontainers modules:**
```python
testcontainers[postgres]>=3.7.1    # PostgreSQL testing
testcontainers[redis]>=3.7.1       # Redis/Cache testing
testcontainers[mysql]>=3.7.1       # MySQL testing (if needed)
```

**Additional testing infrastructure:**
```python
# LocalStack for AWS services (S3, SQS, DynamoDB)
testcontainers-localstack>=3.7.1

# MockServer for external API mocking
testcontainers-mockserver>=3.7.1

# Generic containers for other services
testcontainers>=3.7.1
```

### Test Structure

```
tests/
├── conftest.py                    # Shared fixtures (no mocks!)
├── __init__.py
├── unit/                          # Fast unit tests
│   ├── internal_base/
│   │   ├── conftest.py
│   │   ├── test_logging.py
│   │   ├── test_health.py
│   │   ├── test_resilience.py
│   │   ├── test_secrets.py
│   │   └── test_telemetry.py
│   ├── internal_cache/
│   │   ├── test_config.py
│   │   └── test_locks.py
│   ├── internal_rdbms/
│   │   ├── test_config.py
│   │   ├── test_base.py
│   │   └── test_session.py
│   ├── internal_aws/
│   ├── internal_fastapi/
│   └── internal_http/
└── integration/                   # Real service tests
    ├── internal_cache/
    │   └── test_redis.py         # Real Redis via testcontainers
    ├── internal_rdbms/
    │   ├── test_postgres.py      # Real PostgreSQL via testcontainers
    │   └── test_mysql.py         # Real MySQL via testcontainers
    ├── internal_aws/
    │   ├── test_s3.py            # Real S3 via LocalStack
    │   ├── test_dynamodb.py      # Real DynamoDB via LocalStack
    │   └── test_sqs.py           # Real SQS via LocalStack
    ├── internal_fastapi/
    │   └── test_api.py           # Real FastAPI with dependencies
    └── internal_http/
        └── test_client.py        # Real HTTP calls via MockServer
```

### Test Fixtures Strategy

**Shared fixtures in `tests/conftest.py`:**
```python
@pytest.fixture(scope="session")
def postgres_container():
    """Real PostgreSQL container for integration tests."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres

@pytest.fixture(scope="session")
def redis_container():
    """Real Redis container for integration tests."""
    with RedisContainer("redis:7-alpine") as redis:
        yield redis

@pytest.fixture(scope="session")
def localstack_container():
    """Real LocalStack container for AWS service testing."""
    with LocalStackContainer(image="localstack/localstack:3") as localstack:
        yield localstack

@pytest.fixture(scope="session")
def mockserver_container():
    """Real MockServer container for HTTP API mocking."""
    with MockServerContainer("mockserver/mockserver:latest") as mockserver:
        yield mockserver
```

### Coverage Requirements

- **Minimum**: 90% code coverage
- **Branch coverage**: Required
- **Omit**: Only test files, `__pycache__`, and site-packages
- **Report formats**: HTML, XML, terminal

### Running Tests

```bash
# All tests with coverage
tox

# Unit tests only (fast)
tox -e test-unit

# Integration tests only (requires Docker)
tox -e test-integration

# Specific package unit tests
pytest tests/unit/internal_base -vv --no-cov

# Specific package integration tests
pytest tests/integration/internal_aws -vv --no-cov

# With coverage report
pytest --cov=src --cov-report=html
```

### Test Markers

```python
@pytest.mark.unit           # Fast unit test
@pytest.mark.integration    # Integration test requiring containers
@pytest.mark.slow           # Slow running test
```

---

Generated: 2025-11-03
Repository: python-commons