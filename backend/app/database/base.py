"""SQLAlchemy declarative base and shared mixins."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Base class for all ORM models."""


class IdMixin:
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
