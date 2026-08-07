"""Raw market data endpoints: OHLC candles, symbol info, positions, orders."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_market_data_service, require_api_key
from app.core.constants import Timeframe
from app.schemas.market import OHLCCandle, OHLCResponse
from app.services.broker.schemas import OrderRequest, OrderResult, PositionInfo, SymbolInfo
from app.services.market_data import DEFAULT_OHLC_COUNT, MarketDataService

router = APIRouter(prefix="/market", tags=["market"], dependencies=[Depends(require_api_key)])


@router.get("/ohlc", response_model=OHLCResponse)
def get_ohlc(
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    count: int = DEFAULT_OHLC_COUNT,
    market_data: MarketDataService = Depends(get_market_data_service),
) -> OHLCResponse:
    df = market_data.get_ohlc(symbol.upper(), timeframe, count)
    candles = [OHLCCandle(**row) for row in df.to_dict(orient="records")]
    return OHLCResponse(symbol=symbol.upper(), timeframe=timeframe, candles=candles)


@router.get("/symbol-info", response_model=SymbolInfo)
def get_symbol_info(
    symbol: str, market_data: MarketDataService = Depends(get_market_data_service)
) -> SymbolInfo:
    return market_data.get_symbol_info(symbol.upper())


@router.get("/positions", response_model=list[PositionInfo])
def get_positions(
    market_data: MarketDataService = Depends(get_market_data_service),
) -> list[PositionInfo]:
    return market_data.get_open_positions()


@router.post("/orders", response_model=OrderResult)
def place_order(
    request: OrderRequest, market_data: MarketDataService = Depends(get_market_data_service)
) -> OrderResult:
    return market_data.place_order(request)


@router.delete("/positions/{ticket}", response_model=OrderResult)
def close_position(
    ticket: int, market_data: MarketDataService = Depends(get_market_data_service)
) -> OrderResult:
    return market_data.close_position(ticket)
