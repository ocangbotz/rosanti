"""Pydantic schemas for the generic app_settings key/value store."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class AppSettingUpsert(BaseModel):
    key: str
    value: dict[str, Any]


class AppSettingRead(TimestampedSchema):
    key: str
    value: dict[str, Any]
