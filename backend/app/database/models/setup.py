"""AI-generated trade setups — the auditable output of the analysis pipeline."""

from __future__ import annotations

import enum

from sqlalchemy import JSON, DateTime, Enum, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import Timeframe, TradeDirection
from app.database.base import Base, IdMixin, TimestampMixin


class SetupStatus(str, enum.Enum):
    PROPOSED = "PROPOSED"  # generated, not yet acted on
    TAKEN = "TAKEN"  # trader executed it (linked to a JournalEntry)
    INVALIDATED = "INVALIDATED"  # price action broke the thesis before entry
    EXPIRED = "EXPIRED"  # timed out without being taken or invalidated


class TradeSetup(IdMixin, TimestampMixin, Base):
    """A single "Smart Trade Setup" produced by strategies/setup_generator.py.

    `reasons` and `structure_snapshot` are stored verbatim as JSON so every
    confidence score is reproducible/auditable after the fact — the whole
    point of "explain WHY", not just "what".
    """

    __tablename__ = "trade_setups"

    symbol: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    timeframe: Mapped[Timeframe] = mapped_column(
        Enum(Timeframe, native_enum=False, length=8), nullable=False
    )
    direction: Mapped[TradeDirection] = mapped_column(
        Enum(TradeDirection, native_enum=False, length=8), nullable=False
    )

    entry_price: Mapped[float] = mapped_column(Float, nullable=False)
    stop_loss: Mapped[float] = mapped_column(Float, nullable=False)
    take_profit: Mapped[float] = mapped_column(Float, nullable=False)
    risk_reward: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)

    # list[dict] — each item shaped like strategies.confluence.Reason
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    # Snapshot of the indicator/structure facts the score was computed from.
    structure_snapshot: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    ai_narrative: Mapped[str | None] = mapped_column(String(4000), nullable=True)

    status: Mapped[SetupStatus] = mapped_column(
        Enum(SetupStatus, native_enum=False, length=16),
        default=SetupStatus.PROPOSED,
        nullable=False,
    )
    expires_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<TradeSetup {self.symbol} {self.direction} conf={self.confidence_score:.0f} "
            f"status={self.status}>"
        )
