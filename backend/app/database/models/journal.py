"""Trading journal: executed trades and standalone chart-screenshot analyses."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import TradeDirection, TradeOutcome
from app.database.base import Base, IdMixin, TimestampMixin


class JournalEntry(IdMixin, TimestampMixin, Base):
    """A logged trade — auto-populated from the broker where possible, with
    the AI-generated summary and trader's own notes attached alongside it.
    """

    __tablename__ = "journal_entries"

    setup_id: Mapped[int | None] = mapped_column(
        ForeignKey("trade_setups.id", ondelete="SET NULL"), nullable=True, index=True
    )
    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="SET NULL"), nullable=True, index=True
    )
    mt5_ticket: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    direction: Mapped[TradeDirection] = mapped_column(
        Enum(TradeDirection, native_enum=False, length=8), nullable=False
    )

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    exit_price: Mapped[float | None] = mapped_column(Float, nullable=True)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    lot_size: Mapped[float] = mapped_column(Float, nullable=False)

    risk_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    r_multiple: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    profit_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    outcome: Mapped[TradeOutcome] = mapped_column(
        Enum(TradeOutcome, native_enum=False, length=16),
        default=TradeOutcome.PENDING,
        nullable=False,
    )

    opened_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    ai_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    trader_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    screenshots: Mapped[list[ScreenshotAnalysis]] = relationship(
        back_populates="journal_entry", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<JournalEntry {self.symbol} {self.direction} outcome={self.outcome}>"


class ScreenshotAnalysis(IdMixin, TimestampMixin, Base):
    """A user-uploaded chart screenshot plus the AI's structured report on it.

    Can stand alone (a trader just wants feedback on a chart) or be attached
    to a `JournalEntry` (a screenshot of the actual trade taken).
    """

    __tablename__ = "screenshot_analyses"

    journal_entry_id: Mapped[int | None] = mapped_column(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=True, index=True
    )

    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    symbol_hint: Mapped[str | None] = mapped_column(String(32), nullable=True)

    detected_trend: Mapped[str | None] = mapped_column(String(32), nullable=True)
    detected_support: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    detected_resistance: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    suggested_entry: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_stop_loss: Mapped[float | None] = mapped_column(Float, nullable=True)
    suggested_take_profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    mistakes: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    risk_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    full_report: Mapped[str] = mapped_column(Text, nullable=False)
    raw_model_response: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    journal_entry: Mapped[JournalEntry | None] = relationship(back_populates="screenshots")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<ScreenshotAnalysis id={self.id} trend={self.detected_trend}>"
