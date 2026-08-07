"""Pydantic schemas for risk configuration and calculators."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedSchema


class RiskSettingsUpdate(BaseModel):
    risk_percent: float | None = Field(default=None, gt=0, le=100)
    max_daily_loss_percent: float | None = Field(default=None, gt=0, le=100)
    max_trades_per_day: int | None = Field(default=None, gt=0)
    max_drawdown_percent: float | None = Field(default=None, gt=0, le=100)
    breakeven_trigger_r: float | None = Field(default=None, gt=0)


class RiskSettingsRead(TimestampedSchema):
    account_id: int | None = None
    risk_percent: float
    max_daily_loss_percent: float
    max_trades_per_day: int
    max_drawdown_percent: float
    breakeven_trigger_r: float


class LotSizeRequest(BaseModel):
    account_balance: float = Field(..., gt=0)
    risk_percent: float = Field(..., gt=0, le=100)
    entry_price: float = Field(..., gt=0)
    stop_loss: float = Field(..., gt=0)
    symbol: str
    pip_value_per_lot: float = Field(
        default=10.0,
        gt=0,
        description="Quote-currency value of a 1-pip move for 1 standard lot of this symbol.",
    )
    pip_size: float = Field(default=0.0001, gt=0, description="Price distance representing 1 pip.")


class LotSizeResponse(BaseModel):
    lot_size: float
    risk_amount: float
    stop_loss_pips: float
    pip_value_per_lot: float


class BreakevenRequest(BaseModel):
    entry_price: float
    stop_loss: float
    current_price: float
    direction: str = Field(..., pattern="^(BUY|SELL)$")
    trigger_r: float = Field(default=1.0, gt=0)


class BreakevenResponse(BaseModel):
    current_r_multiple: float
    breakeven_reached: bool
    suggested_new_stop_loss: float | None = None


class DailyLimitCheckRequest(BaseModel):
    account_id: int


class DailyLimitCheckResponse(BaseModel):
    can_trade: bool
    trades_taken_today: int
    max_trades_per_day: int
    daily_pnl_percent: float
    max_daily_loss_percent: float
    reasons: list[str]


class DrawdownInfo(BaseModel):
    peak_equity: float
    trough_equity: float
    current_equity: float
    current_drawdown_percent: float
    max_drawdown_observed_percent: float
    max_drawdown_limit_percent: float
    limit_breached: bool
