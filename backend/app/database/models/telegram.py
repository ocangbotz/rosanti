"""Telegram chats subscribed to trading alerts, with per-category preferences."""

from __future__ import annotations

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class TelegramSubscriber(IdMixin, TimestampMixin, Base):
    __tablename__ = "telegram_subscribers"

    chat_id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(128), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    notify_trade_opened: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_trade_closed: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_sl_tp_hit: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_high_impact_news: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_daily_summary: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    notify_new_setup: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<TelegramSubscriber chat_id={self.chat_id} active={self.is_active}>"
