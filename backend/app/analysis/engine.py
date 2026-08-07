"""Analysis engine orchestrator — the single entry point strategies/ and the
API layer use to turn raw OHLCV into a complete `MarketAnalysis`.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pandas as pd

from app.analysis.indicators import compute_indicator_snapshot
from app.analysis.levels import analyze_levels
from app.analysis.liquidity import analyze_liquidity
from app.analysis.ohlcv import validate_ohlcv
from app.analysis.schemas import MarketAnalysis
from app.analysis.sessions import get_session_info
from app.analysis.structure import analyze_market_structure
from app.analysis.volatility import classify_volatility
from app.core.constants import MIN_CANDLES_FOR_ANALYSIS, Timeframe


class MarketAnalysisEngine:
    """Stateless facade over the individual analysis modules.

    Kept as a class (rather than one big function) so callers can swap
    parameters (swing sensitivity, S/R tolerance, etc.) per-instance without
    threading a dozen kwargs through a free function — an instance is cheap
    and holds no I/O state.
    """

    def __init__(
        self, swing_left: int = 2, swing_right: int = 2, min_candles: int = MIN_CANDLES_FOR_ANALYSIS
    ):
        self.swing_left = swing_left
        self.swing_right = swing_right
        self.min_candles = min_candles

    def analyze(self, df: pd.DataFrame, symbol: str, timeframe: Timeframe) -> MarketAnalysis:
        clean = validate_ohlcv(df, min_candles=self.min_candles)

        indicators = compute_indicator_snapshot(clean)
        structure = analyze_market_structure(
            clean, swing_left=self.swing_left, swing_right=self.swing_right
        )
        liquidity = analyze_liquidity(clean, structure.swing_points, structure.bos_events)
        levels = analyze_levels(clean, structure.swing_points)
        session = get_session_info(clean["time"].iloc[-1].to_pydatetime())
        volatility = classify_volatility(clean)

        return MarketAnalysis(
            symbol=symbol,
            timeframe=timeframe,
            generated_at=datetime.now(UTC),
            candles_analyzed=len(clean),
            indicators=indicators,
            structure=structure,
            liquidity=liquidity,
            levels=levels,
            session=session,
            volatility=volatility,
        )
