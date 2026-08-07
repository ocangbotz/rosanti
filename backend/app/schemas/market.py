"""Pydantic schemas for raw market data endpoints."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.core.constants import Timeframe


class OHLCCandle(BaseModel):
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


class OHLCResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    candles: list[OHLCCandle]
