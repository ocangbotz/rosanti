"""Broker account identity + periodic balance/equity/margin snapshots."""

from __future__ import annotations

from sqlalchemy import Boolean, Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, IdMixin, TimestampMixin


class BrokerAccount(IdMixin, TimestampMixin, Base):
    """A configured MT5 (or mock) trading account.

    `encrypted_password` is optional: most deployments authenticate via
    `.env` (`MT5_LOGIN`/`MT5_PASSWORD`) and never persist credentials at
    all. It exists for the case where a user wants to manage multiple
    saved accounts from the dashboard; when populated it is always a
    Fernet ciphertext (see app/core/security.py), never plaintext.
    """

    __tablename__ = "broker_accounts"

    login: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    server: Mapped[str] = mapped_column(String(128), nullable=False)
    broker_name: Mapped[str] = mapped_column(String(128), default="", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="USD", nullable=False)
    leverage: Mapped[int] = mapped_column(Integer, default=100, nullable=False)
    encrypted_password: Mapped[str | None] = mapped_column(String(512), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    snapshots: Mapped[list[AccountSnapshot]] = relationship(
        back_populates="account",
        cascade="all, delete-orphan",
        order_by="AccountSnapshot.created_at",
    )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<BrokerAccount login={self.login} server={self.server!r}>"


class AccountSnapshot(IdMixin, TimestampMixin, Base):
    """Point-in-time balance/equity/margin reading, polled by the scheduler.

    Powers the equity curve on the Performance page and feeds the risk
    engine's daily-loss / drawdown calculations.
    """

    __tablename__ = "account_snapshots"

    account_id: Mapped[int] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    equity: Mapped[float] = mapped_column(Float, nullable=False)
    margin: Mapped[float] = mapped_column(Float, nullable=False)
    free_margin: Mapped[float] = mapped_column(Float, nullable=False)
    margin_level: Mapped[float | None] = mapped_column(Float, nullable=True)

    account: Mapped[BrokerAccount] = relationship(back_populates="snapshots")

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<AccountSnapshot account_id={self.account_id} equity={self.equity}>"
