# internal_fastapi - Structure Created, Implementation Pending

The directory structure has been created to match ARCHITECTURE.md:

```
internal_fastapi/
├── api/
│   ├── api_service.py (❌ TODO - APIService ABC)
│   ├── config.py (❌ TODO - APIConfig, Environment)
│   ├── fastapi.py (❌ TODO - FastAPISetup)
│   └── lifecycle_manager.py (❌ TODO - LifecycleManager with signal handling)
├── auth/
│   ├── config.py (❌ TODO - AppTokenConfig)
│   └── middleware.py (❌ TODO - AppTokenAuth, TokenAuthMiddleware, helper functions)
├── health/
│   └── endpoint.py (❌ TODO - HealthCheck, create_health_endpoint)
└── logging/
    └── middleware.py (❌ TODO - LoggingMiddleware)
```

## Status
- api/api_service.py - TODO (APIService abstract base class)
- api/config.py - TODO (Environment enum, APIConfig with validation)
- api/fastapi.py - TODO (FastAPISetup with CORS, middleware setup)
- api/lifecycle_manager.py - TODO (LifecycleManager with signal handling, lifespan context)
- auth/config.py - TODO (AppTokenConfig with path exclusions)
- auth/middleware.py - TODO (Token auth middleware with OpenAPI integration)
- health/endpoint.py - TODO (HealthCheck with async checks support)
- logging/middleware.py - TODO (Request/response logging middleware)

## Key Features to Implement

### API Module
1. **APIService**: Abstract base class for FastAPI services
2. **APIConfig**: Configuration model with Environment enum (DEV/STAGE/PROD)
3. **FastAPISetup**: Main setup class integrating all components
4. **LifecycleManager**:
   - Service lifecycle management
   - Signal handling (SIGTERM, SIGINT)
   - Async startup/shutdown
   - Integration with internal_base.AsyncService

### Auth Module
1. **AppTokenConfig**: Token config with path exclusions (supports glob patterns)
2. **AppTokenAuth**: Token validator with excluded paths
3. **TokenAuthMiddleware**: Middleware with OpenAPI schema integration
4. **Helper Functions**: setup_token_auth, apply_token_auth_middleware

### Health Module
1. **HealthCheck**: Manager for health checks
2. **HealthResponse**: Pydantic model for responses
3. **create_health_endpoint**: Factory function with custom checks support

### Logging Module
1. **LoggingMiddleware**: Request/response logging with timing

## Next Steps
1. Implement all API module files (~400 lines)
2. Implement auth module with middleware (~300 lines)
3. Implement health endpoint with async checks (~150 lines)
4. Implement logging middleware (~100 lines)
5. Create comprehensive examples for each module
6. Remove old files (pagination.py, responses.py, middleware.py, dependencies.py, errors.py)
7. Update main __init__.py to export new API

## Dependencies
- fastapi>=0.100.0
- uvicorn[standard]>=0.23.0
- internal-base (for LoggingConfig, AsyncService integration)

## Estimated Effort
Total ~1000+ lines across 8 files with comprehensive docstrings and examples.
