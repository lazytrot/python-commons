"""
Datetime utilities for database operations.

Provides decorators and helpers for datetime handling.
"""

from datetime import datetime, timezone
from typing import Callable
from functools import wraps


def ensure_utc(func: Callable[..., datetime]) -> property:
    """
    Decorator that wraps property getters to ensure datetime values are UTC-aware.

    Converts naive datetimes to UTC and ensures aware datetimes are in UTC timezone.
    Useful for database models where timestamps should always be UTC-aware.

    Args:
        func: Property getter function that returns a datetime

    Returns:
        Property with UTC-aware datetime guarantee

    Example:
        from datetime import datetime
        from sqlalchemy import DateTime
        from sqlalchemy.orm import Mapped, mapped_column
        from internal_rdbms.utils import ensure_utc

        class User(Base):
            __tablename__ = "users"

            id: Mapped[int] = mapped_column(primary_key=True)
            _created_at: Mapped[datetime] = mapped_column(
                "created_at",
                DateTime,
                nullable=False
            )

            @property
            @ensure_utc
            def created_at(self) -> datetime:
                return self._created_at

            @created_at.setter
            def created_at(self, value: datetime) -> None:
                self._created_at = value

        # Usage
        user = User()
        user.created_at = datetime(2024, 1, 1, 12, 0, 0)  # Naive datetime
        print(user.created_at)  # 2024-01-01 12:00:00+00:00 (UTC-aware)
    """
    @wraps(func)
    def wrapper(self) -> datetime:
        value = func(self)
        if value is None:
            return value

        # If already timezone-aware, convert to UTC
        if value.tzinfo is not None:
            return value.astimezone(timezone.utc)

        # If naive, assume UTC
        return value.replace(tzinfo=timezone.utc)

    return property(wrapper)
