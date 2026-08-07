"""Pydantic schemas for the trading journal and screenshot analysis."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.core.constants import TradeDirection, TradeOutcome
from app.schemas.common import TimestampedSchema


class JournalEntryCreate(BaseModel):
    setup_id: int | None = None
    account_id: int | None = None
    mt5_ticket: int | None = None
    symbol: str
    direction: TradeDirection
    entry_price: float
    stop_loss: float
    take_profit: float
    lot_size: float = Field(..., gt=0)
    risk_percent: float | None = None
    opened_at: datetime
    trader_notes: str | None = None


class JournalEntryUpdate(BaseModel):
    exit_price: float | None = None
    closed_at: datetime | None = None
    outcome: TradeOutcome | None = None
    profit_loss: float | None = None
    profit_loss_percent: float | None = None
    r_multiple: float | None = None
    ai_summary: str | None = None
    trader_notes: str | None = None


class JournalEntryRead(TimestampedSchema):
    setup_id: int | None = None
    account_id: int | None = None
    mt5_ticket: int | None = None
    symbol: str
    direction: TradeDirection
    entry_price: float
    exit_price: float | None = None
    stop_loss: float
    take_profit: float
    lot_size: float
    risk_percent: float | None = None
    r_multiple: float | None = None
    profit_loss: float | None = None
    profit_loss_percent: float | None = None
    outcome: TradeOutcome
    opened_at: datetime
    closed_at: datetime | None = None
    ai_summary: str | None = None
    trader_notes: str | None = None


class ScreenshotAnalysisRead(TimestampedSchema):
    journal_entry_id: int | None = None
    file_path: str
    symbol_hint: str | None = None
    detected_trend: str | None = None
    detected_support: list[float]
    detected_resistance: list[float]
    suggested_entry: float | None = None
    suggested_stop_loss: float | None = None
    suggested_take_profit: float | None = None
    mistakes: list[str]
    risk_notes: str | None = None
    full_report: str


class WinRateReport(BaseModel):
    total_trades: int
    wins: int
    losses: int
    breakevens: int
    win_rate_percent: float
    average_r_multiple: float | None = None
    total_profit_loss: float


class PeriodReport(BaseModel):
    period_start: datetime
    period_end: datetime
    trades: list[JournalEntryRead]
    win_rate: WinRateReport
    net_profit_loss: float
    best_trade: JournalEntryRead | None = None
    worst_trade: JournalEntryRead | None = None
