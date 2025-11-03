"""
Abstract API service base class.

Provides base class for FastAPI service implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional

from fastapi import FastAPI


class APIService(ABC):
    """
    Abstract API service base class.

    Base class for implementing FastAPI services with automatic route setup.
    Subclasses must implement _setup_routes() to define their endpoints.

    Example:
        from fastapi import FastAPI
        from internal_fastapi import APIService

        class UserService(APIService):
            '''User management service.'''

            def _setup_routes(self) -> None:
                '''Setup user routes.'''

                @self.app.get("/users")
                async def list_users():
                    return {"users": []}

                @self.app.get("/users/{user_id}")
                async def get_user(user_id: str):
                    return {"user_id": user_id}

                @self.app.post("/users")
                async def create_user(name: str, email: str):
                    return {"user_id": "123", "name": name, "email": email}

        # Usage
        app = FastAPI()
        user_service = UserService(app, name="users")
        # Routes are automatically registered
    """

    def __init__(self, app: FastAPI, name: Optional[str] = None):
        """
        Initialize API service.

        Args:
            app: FastAPI application instance
            name: Service name (defaults to class name)

        Example:
            app = FastAPI()
            service = MyService(app, name="my_service")
        """
        self.app = app
        self.name = name or self.__class__.__name__
        self._setup_routes()

    @abstractmethod
    def _setup_routes(self) -> None:
        """
        Setup service routes.

        Must be implemented by subclasses to define API endpoints.

        Example:
            def _setup_routes(self) -> None:
                @self.app.get("/health")
                async def health():
                    return {"status": "ok"}

                @self.app.post("/data")
                async def post_data(data: dict):
                    return {"received": data}
        """
        pass
