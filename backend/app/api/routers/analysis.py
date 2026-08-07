"""Market analysis endpoints: full structured analysis + AI narrative."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.analysis.engine import MarketAnalysisEngine
from app.analysis.schemas import MarketAnalysis
from app.api.deps import get_ai_narrator, get_market_data_service, require_api_key
from app.core.constants import Timeframe
from app.services.ai.narrator import MarketNarrator
from app.services.market_data import DEFAULT_OHLC_COUNT, MarketDataService

router = APIRouter(prefix="/analysis", tags=["analysis"], dependencies=[Depends(require_api_key)])


def _run_analysis(
    symbol: str, timeframe: Timeframe, count: int, market_data: MarketDataService
) -> MarketAnalysis:
    df = market_data.get_ohlc(symbol.upper(), timeframe, count)
    return MarketAnalysisEngine().analyze(df, symbol.upper(), timeframe)


@router.get("", response_model=MarketAnalysis)
def get_market_analysis(
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    count: int = DEFAULT_OHLC_COUNT,
    market_data: MarketDataService = Depends(get_market_data_service),
) -> MarketAnalysis:
    return _run_analysis(symbol, timeframe, count, market_data)


class NarrativeResponse(BaseModel):
    symbol: str
    timeframe: Timeframe
    narrative: str


@router.get("/narrative", response_model=NarrativeResponse)
async def get_market_narrative(
    symbol: str,
    timeframe: Timeframe = Timeframe.H1,
    count: int = DEFAULT_OHLC_COUNT,
    market_data: MarketDataService = Depends(get_market_data_service),
    narrator: MarketNarrator = Depends(get_ai_narrator),
) -> NarrativeResponse:
    analysis = _run_analysis(symbol, timeframe, count, market_data)
    narrative = await narrator.narrate(analysis)
    return NarrativeResponse(symbol=symbol.upper(), timeframe=timeframe, narrative=narrative)
