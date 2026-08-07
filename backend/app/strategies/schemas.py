"""Result types produced by the strategy layer (confluence scoring + setup
generation) — the shapes the API layer persists into `TradeSetup` rows.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from app.core.constants import Timeframe, TradeDirection
from app.schemas.setup import Reason


class _Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ConfluenceResult(_Model):
    """The scored outcome for a single direction (BUY or SELL)."""

    direction: TradeDirection
    confidence: float  # 0-100
    reasons: list[Reason]


class TradeSetupProposal(_Model):
    """A concrete, ready-to-persist trade idea."""

    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    confidence_score: float
    reasons: list[Reason]
    structure_snapshot: dict


class SetupGenerationResult(_Model):
    """Always returned — even a "no trade" decision must explain why, per
    the product requirement that the assistant never stays silent about its
    reasoning."""

    symbol: str
    timeframe: Timeframe
    has_valid_setup: bool
    setup: TradeSetupProposal | None = None
    dominant_direction: TradeDirection
    confidence: float
    reasons: list[Reason]
    rejection_reason: str | None = None
