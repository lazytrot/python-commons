"""
Logging middleware for request/response logging.

Provides middleware for logging HTTP requests and responses.
"""

import time
import logging
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Request/response logging middleware.

    Logs HTTP requests and responses with timing information.

    Example:
        from fastapi import FastAPI
        from internal_fastapi import LoggingMiddleware

        app = FastAPI()
        app.add_middleware(LoggingMiddleware)

        @app.get("/users")
        async def get_users():
            return {"users": []}

        # Logs:
        # INFO - Request: GET /users from 127.0.0.1
        # INFO - Response: GET /users - 200 OK (15.2ms)
    """

    async def dispatch(
        self,
        request: Request,
        call_next: RequestResponseEndpoint
    ) -> Response:
        """
        Dispatch request with logging.

        Args:
            request: FastAPI request
            call_next: Next middleware

        Returns:
            Response with timing header

        Example:
            # Called automatically by FastAPI middleware system
            # Logs request and response with timing
            response = await middleware.dispatch(request, call_next)
        """
        # Get client info
        client_host = request.client.host if request.client else "unknown"

        # Log request
        logger.info(
            f"Request: {request.method} {request.url.path} "
            f"from {client_host}"
        )

        # Track timing
        start_time = time.time()

        try:
            # Process request
            response = await call_next(request)

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Log response
            logger.info(
                f"Response: {request.method} {request.url.path} - "
                f"{response.status_code} ({duration_ms:.1f}ms)"
            )

            # Add timing header
            response.headers["X-Process-Time"] = f"{duration_ms:.1f}ms"

            return response

        except Exception as e:
            # Calculate duration for error case
            duration_ms = (time.time() - start_time) * 1000

            # Log error
            logger.error(
                f"Error: {request.method} {request.url.path} - "
                f"{type(e).__name__}: {e} ({duration_ms:.1f}ms)",
                exc_info=True
            )

            # Re-raise to let FastAPI handle it
            raise
