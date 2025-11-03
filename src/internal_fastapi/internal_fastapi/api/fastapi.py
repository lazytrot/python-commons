"""
FastAPI application setup and configuration.

Provides utilities for setting up FastAPI applications with standard configuration.
"""

from typing import Callable, Awaitable, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import APIConfig
from .lifecycle_manager import LifecycleManager

try:
    from internal_base import LoggingConfig, configure_logging, BackgroundServiceProtocol
except ImportError:
    # Fallback types if internal_base not available
    LoggingConfig = None
    configure_logging = None
    BackgroundServiceProtocol = None


class FastAPISetup:
    """
    FastAPI application setup and configuration.

    Provides a simplified way to create and configure FastAPI applications
    with standard middleware, CORS, logging, and lifecycle management.

    Example:
        from internal_fastapi import FastAPISetup, APIConfig, LifecycleManager
        from internal_base import LoggingConfig, LogFormat

        # Create configurations
        api_config = APIConfig(
            title="My API",
            version="1.0.0",
            debug=True,
            cors_origins=["http://localhost:3000"]
        )

        log_config = LoggingConfig(
            format=LogFormat.JSON,
            level="INFO"
        )

        # Setup handler for services
        async def setup_services():
            service = MyBackgroundService()
            return [service]

        # Create FastAPI app
        setup = FastAPISetup(api_config, log_config, setup_services)
        app = setup.create_fastapi_app()

        # Run with uvicorn
        if __name__ == "__main__":
            import uvicorn
            uvicorn.run(
                app,
                host=api_config.host,
                port=api_config.port,
                reload=api_config.reload
            )
    """

    def __init__(
        self,
        api_config: APIConfig,
        log_config: "LoggingConfig" = None,
        setup_handler: Callable[[], Awaitable[List["BackgroundServiceProtocol"]]] = None
    ):
        """
        Initialize FastAPI setup.

        Args:
            api_config: API configuration
            log_config: Logging configuration (optional)
            setup_handler: Service setup handler (optional)

        Example:
            api_config = APIConfig(title="My API", version="1.0.0")
            log_config = LoggingConfig(format=LogFormat.JSON)

            async def setup():
                return [MyService()]

            setup = FastAPISetup(api_config, log_config, setup)
        """
        self.api_config = api_config
        self.log_config = log_config
        self.setup_handler = setup_handler

        # Configure logging if available
        if configure_logging and log_config:
            configure_logging(log_config)

    def create_fastapi_app(self) -> FastAPI:
        """
        Create configured FastAPI application.

        Creates a FastAPI app with:
        - Lifecycle management for background services
        - CORS middleware
        - API metadata (title, description, version)
        - Debug mode configuration

        Returns:
            Configured FastAPI application

        Example:
            setup = FastAPISetup(api_config)
            app = setup.create_fastapi_app()

            @app.get("/")
            async def root():
                return {"message": "Hello World"}

            # Run with uvicorn
            uvicorn.run(app, host="0.0.0.0", port=8000)
        """
        # Create lifecycle manager
        lifecycle_manager = LifecycleManager()

        # Create FastAPI app with lifespan
        app = FastAPI(
            title=self.api_config.title,
            description=self.api_config.description,
            version=self.api_config.version,
            debug=self.api_config.debug,
            lifespan=lifecycle_manager.fastapi_lifespan(self.setup_handler)
        )

        # Add CORS middleware
        app.add_middleware(
            CORSMiddleware,
            allow_origins=self.api_config.cors_origins,
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        return app
