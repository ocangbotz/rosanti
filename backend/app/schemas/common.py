"""Shared Pydantic base classes and small reusable schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class ORMBase(BaseModel):
    """Base for schemas that are read directly from SQLAlchemy ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class TimestampedSchema(ORMBase):
    id: int
    created_at: datetime
    updated_at: datetime


class Page(ORMBase, Generic[T]):
    items: list[T]
    total: int
    page: int
    page_size: int

    @property
    def total_pages(self) -> int:
        if self.page_size <= 0:
            return 0
        return (self.total + self.page_size - 1) // self.page_size
