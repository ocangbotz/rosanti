"""Pydantic schemas for Telegram subscriber management."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TimestampedSchema


class TelegramSubscriberCreate(BaseModel):
    chat_id: str
    username: str | None = None


class TelegramPreferencesUpdate(BaseModel):
    is_active: bool | None = None
    notify_trade_opened: bool | None = None
    notify_trade_closed: bool | None = None
    notify_sl_tp_hit: bool | None = None
    notify_high_impact_news: bool | None = None
    notify_daily_summary: bool | None = None
    notify_new_setup: bool | None = None


class TelegramSubscriberRead(TimestampedSchema):
    chat_id: str
    username: str | None = None
    is_active: bool
    notify_trade_opened: bool
    notify_trade_closed: bool
    notify_sl_tp_hit: bool
    notify_high_impact_news: bool
    notify_daily_summary: bool
    notify_new_setup: bool


class TelegramTestMessageRequest(BaseModel):
    chat_id: str | None = None
    message: str = "✅ Fathir AI Trading Assistant is connected."
