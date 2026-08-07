import pytest

from app.analysis.engine import MarketAnalysisEngine
from app.core.constants import Timeframe, TradeDirection
from app.core.exceptions import InsufficientDataError
from tests.factories import make_ohlcv, make_trend_then_reversal_ohlcv


def test_engine_produces_full_analysis():
    df = make_trend_then_reversal_ohlcv(n=260)
    engine = MarketAnalysisEngine()
    result = engine.analyze(df, symbol="EURUSD", timeframe=Timeframe.H1)

    assert result.symbol == "EURUSD"
    assert result.timeframe == Timeframe.H1
    assert result.candles_analyzed == 260
    assert result.indicators.price > 0
    assert result.structure.trend in {
        TradeDirection.BUY,
        TradeDirection.SELL,
        TradeDirection.NEUTRAL,
    }
    assert isinstance(result.liquidity.order_blocks, list)
    assert isinstance(result.levels.support_resistance, list)
    assert result.session is not None
    assert result.volatility.atr >= 0


def test_engine_raises_on_insufficient_history():
    df = make_ohlcv(n=50)
    engine = MarketAnalysisEngine()
    with pytest.raises(InsufficientDataError):
        engine.analyze(df, symbol="EURUSD", timeframe=Timeframe.H1)


def test_engine_is_deterministic_for_same_input():
    df = make_trend_then_reversal_ohlcv(n=260)
    engine = MarketAnalysisEngine()
    result_a = engine.analyze(df, symbol="EURUSD", timeframe=Timeframe.H1)
    result_b = engine.analyze(df, symbol="EURUSD", timeframe=Timeframe.H1)
    assert result_a.indicators.model_dump() == result_b.indicators.model_dump()
    assert result_a.structure.trend == result_b.structure.trend
    assert len(result_a.structure.bos_events) == len(result_b.structure.bos_events)
