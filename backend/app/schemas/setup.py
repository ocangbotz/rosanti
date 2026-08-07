"""Pydantic schemas for AI-generated trade setups."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import Timeframe, TradeDirection
from app.database.models.setup import SetupStatus
from app.schemas.common import TimestampedSchema


class Reason(BaseModel):
    """A single confluence factor that fed into a setup's confidence score.

    This is the atomic unit of "explain WHY" — every `TradeSetup.reasons`
    entry is one of these, and the AI narrator is only allowed to describe
    them, never invent new ones.
    """

    factor: str = Field(..., description="Machine-readable factor id, e.g. 'bullish_bos'.")
    description: str = Field(
        ..., description="Human-readable explanation, e.g. 'Bullish BOS confirmed'."
    )
    direction: TradeDirection
    weight: float = Field(..., ge=0, le=100, description="Contribution to the confidence score.")


class TradeSetupRead(TimestampedSchema):
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
    ai_narrative: str | None = None
    status: SetupStatus
    expires_at: datetime | None = None


class TradeSetupSummary(BaseModel):
    """Lightweight shape for list views (dashboard cards, Telegram alerts)."""

    id: int
    symbol: str
    timeframe: Timeframe
    direction: TradeDirection
    confidence_score: float
    risk_reward: float
    status: SetupStatus
    created_at: datetime


class GenerateSetupRequest(BaseModel):
    symbol: str
    timeframe: Timeframe = Timeframe.H1
    risk_percent: float | None = Field(
        default=None, ge=0.01, le=100, description="Overrides the account's default risk %."
    )
    include_ai_narrative: bool = True
