"""Pydantic schemas for the economic calendar / news filter."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.constants import NewsImpact
from app.schemas.common import TimestampedSchema


class NewsEventRead(TimestampedSchema):
    title: str
    country: str
    currency: str | None = None
    impact: NewsImpact
    event_time: datetime
    forecast: str | None = None
    previous: str | None = None
    actual: str | None = None
    source: str


class NewsWarning(TimestampedSchema):
    """Trimmed shape used specifically for pre-trade warnings and Telegram alerts."""

    title: str
    currency: str | None = None
    impact: NewsImpact
    event_time: datetime
    minutes_until: float


class NewsCheckResponse(BaseModel):
    has_high_impact_soon: bool
    lookahead_minutes: int
    events: list[NewsWarning]
