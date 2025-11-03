"""
Database configuration models.

Provides Pydantic models for database configuration.
"""

from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, computed_field


class DatabaseConfig(BaseModel):
    """Database connection configuration."""

    driver: str = Field(
        default="mysql+aiomysql",
        description="Database driver (e.g., mysql+aiomysql, postgresql+asyncpg, sqlite+aiosqlite)"
    )
    host: str = Field(
        default="localhost",
        description="Database host"
    )
    port: Optional[int] = Field(
        default=None,
        description="Database port (default: 3306 for MySQL, 5432 for PostgreSQL)"
    )
    user: Optional[str] = Field(
        default=None,
        description="Database user"
    )
    password: Optional[str] = Field(
        default=None,
        description="Database password",
        repr=False
    )
    name: str = Field(
        default="agent_framework",
        description="Database name"
    )
    echo: bool = Field(
        default=False,
        description="Echo SQL statements for debugging"
    )
    pool_size: int = Field(
        default=5,
        description="Connection pool size"
    )
    max_overflow: int = Field(
        default=10,
        description="Maximum overflow connections beyond pool_size"
    )
    pool_timeout: float = Field(
        default=30.0,
        description="Seconds to wait before giving up on getting a connection"
    )
    pool_recycle: int = Field(
        default=1800,
        description="Recycle connections after this many seconds"
    )
    connect_args: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional database-specific connection arguments"
    )

    @computed_field
    @property
    def url(self) -> str:
        """
        Compute connection URL from configuration.

        Returns:
            Database connection URL

        Examples:
            MySQL: mysql+aiomysql://user:pass@localhost:3306/mydb
            PostgreSQL: postgresql+asyncpg://user:pass@localhost:5432/mydb
            SQLite: sqlite+aiosqlite:///./database.db
            SQLite memory: sqlite+aiosqlite:///:memory:
        """
        # SQLite in-memory
        if self.driver.startswith("sqlite") and self.name == ":memory:":
            return f"{self.driver}:///:memory:"

        # SQLite file-based
        if self.driver.startswith("sqlite"):
            return f"{self.driver}:///./{self.name}"

        # Network databases (MySQL, PostgreSQL, etc.)
        port = self.port
        if port is None:
            if "mysql" in self.driver:
                port = 3306
            elif "postgres" in self.driver:
                port = 5432
            else:
                port = 3306  # default

        user_pass = ""
        if self.user:
            user_pass = self.user
            if self.password:
                user_pass = f"{user_pass}:{self.password}"
            user_pass = f"{user_pass}@"

        return f"{self.driver}://{user_pass}{self.host}:{port}/{self.name}"

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
