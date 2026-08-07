"""Risk configuration and per-day performance tracking used to enforce limits."""

from __future__ import annotations

from datetime import date as date_type

from sqlalchemy import Date, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, IdMixin, TimestampMixin


class RiskSettings(IdMixin, TimestampMixin, Base):
    """Per-account risk configuration. One active row per account.

    A `NULL` `account_id` row acts as the global default applied before any
    account-specific override exists (see risk/limits.py).
    """

    __tablename__ = "risk_settings"

    account_id: Mapped[int | None] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=True, unique=True
    )
    risk_percent: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    max_daily_loss_percent: Mapped[float] = mapped_column(Float, default=3.0, nullable=False)
    max_trades_per_day: Mapped[int] = mapped_column(Integer, default=5, nullable=False)
    max_drawdown_percent: Mapped[float] = mapped_column(Float, default=10.0, nullable=False)
    breakeven_trigger_r: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<RiskSettings account_id={self.account_id} risk%={self.risk_percent}>"


class DailyPerformance(IdMixin, TimestampMixin, Base):
    """One row per (account, calendar date) — the running ledger the risk
    engine reads to enforce max-trades-per-day and daily-loss-limit rules
    without having to re-scan the full journal on every request.
    """

    __tablename__ = "daily_performance"
    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_daily_performance_account_date"),
    )

    account_id: Mapped[int] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[date_type] = mapped_column(Date, nullable=False, index=True)
    starting_equity: Mapped[float] = mapped_column(Float, nullable=False)
    ending_equity: Mapped[float | None] = mapped_column(Float, nullable=True)
    realized_pnl: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    trades_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    max_intraday_drawdown_percent: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<DailyPerformance {self.date} account_id={self.account_id} pnl={self.realized_pnl}>"
        )
