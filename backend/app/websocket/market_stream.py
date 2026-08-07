"""Live market-data streaming over WebSocket.

Each connection runs its own pull loop (fetch → analyze → send → sleep)
rather than subscribing to a shared broadcast — this keeps per-connection
symbol/timeframe selection trivial and avoids coordinating fan-out state,
at the cost of duplicating the analysis call across concurrently-open
connections watching the same symbol. That trade-off is fine at the scale
this is a personal trading tool operates at (see docs/ARCHITECTURE.md §7).
"""

from __future__ import annotations

import asyncio

from fastapi import WebSocket, WebSocketDisconnect

from app.analysis.engine import MarketAnalysisEngine
from app.analysis.schemas import MarketAnalysis
from app.core.constants import Timeframe
from app.core.exceptions import FathirError
from app.core.logging_config import get_logger
from app.services.market_data import MarketDataService

logger = get_logger(__name__)


def build_stream_payload(analysis: MarketAnalysis) -> dict:
    """The compact per-tick payload sent to dashboard clients — deliberately
    smaller than the full `/analysis` REST response (which includes every
    swing point, order block, FVG, etc.) since this fires repeatedly."""
    return {
        "type": "market_update",
        "symbol": analysis.symbol,
        "timeframe": analysis.timeframe.value,
        "generated_at": analysis.generated_at.isoformat(),
        "price": analysis.indicators.price,
        "ema_trend_bias": analysis.indicators.ema_trend_bias.value,
        "rsi14": analysis.indicators.rsi14,
        "structure_trend": analysis.structure.trend.value,
        "last_bos": (
            {
                "direction": analysis.structure.last_bos.direction.value,
                "price": analysis.structure.last_bos.price,
            }
            if analysis.structure.last_bos
            else None
        ),
        "last_choch": (
            {
                "direction": analysis.structure.last_choch.direction.value,
                "price": analysis.structure.last_choch.price,
            }
            if analysis.structure.last_choch
            else None
        ),
        "session": analysis.session.session.value,
        "volatility_regime": analysis.volatility.regime.value,
    }


async def stream_market_data(
    websocket: WebSocket,
    symbol: str,
    timeframe: Timeframe,
    market_data: MarketDataService,
    interval_seconds: float,
) -> None:
    """Accept the connection and push analysis updates until the client
    disconnects or the socket errors out."""
    await websocket.accept()
    engine = MarketAnalysisEngine()
    try:
        while True:
            try:
                df = market_data.get_ohlc(symbol, timeframe)
                analysis = engine.analyze(df, symbol, timeframe)
                await websocket.send_json(build_stream_payload(analysis))
            except FathirError as exc:
                await websocket.send_json({"type": "error", "message": exc.message})
            await asyncio.sleep(interval_seconds)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected from %s %s stream.", symbol, timeframe.value)
