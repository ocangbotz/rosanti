"""Shared enums and constants used across analysis, strategy, and API layers."""

from __future__ import annotations

from enum import Enum


class Timeframe(str, Enum):
    M1 = "M1"
    M5 = "M5"
    M15 = "M15"
    M30 = "M30"
    H1 = "H1"
    H4 = "H4"
    D1 = "D1"
    W1 = "W1"

    @property
    def minutes(self) -> int:
        return {
            Timeframe.M1: 1,
            Timeframe.M5: 5,
            Timeframe.M15: 15,
            Timeframe.M30: 30,
            Timeframe.H1: 60,
            Timeframe.H4: 240,
            Timeframe.D1: 1440,
            Timeframe.W1: 10080,
        }[self]


class TradeDirection(str, Enum):
    BUY = "BUY"
    SELL = "SELL"
    NEUTRAL = "NEUTRAL"


class TradingSession(str, Enum):
    SYDNEY = "SYDNEY"
    TOKYO = "TOKYO"
    LONDON = "LONDON"
    NEW_YORK = "NEW_YORK"
    OFF_HOURS = "OFF_HOURS"


class VolatilityRegime(str, Enum):
    LOW = "LOW"
    NORMAL = "NORMAL"
    HIGH = "HIGH"
    EXTREME = "EXTREME"


class NewsImpact(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class TradeStatus(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"


class TradeOutcome(str, Enum):
    WIN = "WIN"
    LOSS = "LOSS"
    BREAKEVEN = "BREAKEVEN"
    PENDING = "PENDING"


# Trading session windows in UTC (approximate, DST-naive — good enough for
# session-tagging heuristics; not used for anything execution-critical).
SESSION_WINDOWS_UTC: dict[TradingSession, tuple[int, int]] = {
    TradingSession.SYDNEY: (21, 6),
    TradingSession.TOKYO: (0, 9),
    TradingSession.LONDON: (7, 16),
    TradingSession.NEW_YORK: (12, 21),
}

# Minimum number of candles required before structure/indicator analysis is
# considered statistically meaningful.
MIN_CANDLES_FOR_ANALYSIS = 210  # covers EMA200 warm-up with margin

# High-impact economic events we explicitly flag by keyword match.
HIGH_IMPACT_EVENT_KEYWORDS = (
    "non-farm payrolls",
    "nonfarm payrolls",
    "nfp",
    "cpi",
    "consumer price index",
    "fomc",
    "federal funds rate",
    "interest rate decision",
    "rate decision",
    "gdp",
    "unemployment rate",
    "ecb press conference",
    "ecb interest rate",
    "boe interest rate",
    "boj interest rate",
)
