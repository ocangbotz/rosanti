"""WebSocket routes."""

from __future__ import annotations

from fastapi import APIRouter, WebSocket

from app.config import get_settings
from app.core.constants import Timeframe
from app.services.broker.factory import get_broker_gateway
from app.services.market_data import MarketDataService
from app.websocket.market_stream import stream_market_data

router = APIRouter()


@router.websocket("/ws/market")
async def market_ws(
    websocket: WebSocket, symbol: str = "EURUSD", timeframe: Timeframe = Timeframe.H1
) -> None:
    settings = get_settings()
    market_data = MarketDataService(get_broker_gateway())
    await stream_market_data(
        websocket,
        symbol.upper(),
        timeframe,
        market_data,
        interval_seconds=float(settings.market_poll_interval_seconds),
    )
