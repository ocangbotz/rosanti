"""Economic calendar events, cached locally so the app can warn even between polls."""

from __future__ import annotations

from sqlalchemy import DateTime, Enum, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import NewsImpact
from app.database.base import Base, IdMixin, TimestampMixin


class NewsEvent(IdMixin, TimestampMixin, Base):
    __tablename__ = "news_events"

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    country: Mapped[str] = mapped_column(String(8), nullable=False, index=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    impact: Mapped[NewsImpact] = mapped_column(
        Enum(NewsImpact, native_enum=False, length=8), nullable=False, index=True
    )
    event_time: Mapped[DateTime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    forecast: Mapped[str | None] = mapped_column(String(64), nullable=True)
    previous: Mapped[str | None] = mapped_column(String(64), nullable=True)
    actual: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, default="forexfactory")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<NewsEvent {self.title!r} impact={self.impact} at={self.event_time}>"
