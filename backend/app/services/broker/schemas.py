"""Data contracts for the broker gateway layer — symbol metadata, open
positions, and order requests/results. Kept separate from `app/schemas/`
because these describe the *broker's* view of the world (matches MT5's
field names closely), not the API's request/response shapes.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import TradeDirection


class _Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class SymbolInfo(_Model):
    symbol: str
    bid: float
    ask: float
    spread_points: int
    point: float
    digits: int
    contract_size: float
    volume_min: float
    volume_max: float
    volume_step: float
    pip_size: float
    pip_value_per_lot: float


class PositionInfo(_Model):
    ticket: int
    symbol: str
    direction: TradeDirection
    volume: float
    open_price: float
    current_price: float
    stop_loss: float | None = None
    take_profit: float | None = None
    profit: float
    swap: float
    opened_at: datetime


class OrderRequest(_Model):
    symbol: str
    direction: TradeDirection
    volume: float
    stop_loss: float | None = None
    take_profit: float | None = None
    comment: str = "Fathir AI Trading Assistant"


class OrderResult(_Model):
    success: bool
    ticket: int | None = None
    executed_price: float | None = None
    message: str = ""
